#include "openfhe.h"
#include "model_input.h"

#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

using lbcrypto::Ciphertext;
using lbcrypto::CryptoContext;
using lbcrypto::CryptoContextCKKSRNS;
using lbcrypto::DCRTPoly;
using lbcrypto::GenCryptoContext;
using lbcrypto::KeyPair;
using lbcrypto::Plaintext;

namespace {

struct ClientKeys {
    KeyPair<DCRTPoly> key_pair;
};

struct VerificationResult {
    double plain_logit;
    double fhe_logit;
    double absolute_error;
    double relative_error;
};

CryptoContext<DCRTPoly> CreateContext() {
    lbcrypto::CCParams<CryptoContextCKKSRNS> parameters;
    // One ciphertext-plaintext multiplication is the only multiplicative level
    // used by the encrypted linear model.
    parameters.SetMultiplicativeDepth(1);
    parameters.SetScalingModSize(50);
    // CKKS batch sizes must be powers of two. Seven features fit in eight slots.
    parameters.SetBatchSize(8);

    auto context = GenCryptoContext(parameters);
    context->Enable(lbcrypto::PKE);
    context->Enable(lbcrypto::KEYSWITCH);
    context->Enable(lbcrypto::LEVELEDSHE);
    return context;
}

ClientKeys GenerateClientKeys(const CryptoContext<DCRTPoly>& context) {
    auto key_pair = context->KeyGen();
    if (!key_pair.good()) {
        throw std::runtime_error("OpenFHE key generation failed");
    }
    // Evaluation keys can be shared with the evaluator. The secret key stays
    // inside ClientKeys and is never passed to ServerWeightedSum.
    context->EvalMultKeyGen(key_pair.secretKey);
    return {key_pair};
}

std::vector<Ciphertext<DCRTPoly>> ClientEncryptFeatures(
    const CryptoContext<DCRTPoly>& context,
    const lbcrypto::PublicKey<DCRTPoly>& public_key) {
    std::vector<Ciphertext<DCRTPoly>> encrypted;
    encrypted.reserve(credit_risk::kFeatureCount);
    for (double feature : credit_risk::kScaledFeatures) {
        auto plaintext = context->MakeCKKSPackedPlaintext(std::vector<double>{feature});
        encrypted.push_back(context->Encrypt(public_key, plaintext));
    }
    return encrypted;
}

// SERVER BOUNDARY: this function receives ciphertexts and public model
// parameters only. It has no secret key and cannot decrypt features or logits.
Ciphertext<DCRTPoly> ServerWeightedSum(
    const CryptoContext<DCRTPoly>& context,
    const std::vector<Ciphertext<DCRTPoly>>& encrypted_features) {
    if (encrypted_features.size() != credit_risk::kFeatureCount) {
        throw std::runtime_error("Unexpected encrypted feature count");
    }

    auto encrypted_logit = context->EvalMult(encrypted_features[0], credit_risk::kWeights[0]);
    for (std::size_t index = 1; index < credit_risk::kFeatureCount; ++index) {
        auto weighted_feature = context->EvalMult(encrypted_features[index], credit_risk::kWeights[index]);
        encrypted_logit = context->EvalAdd(encrypted_logit, weighted_feature);
    }
    return context->EvalAdd(encrypted_logit, credit_risk::kBias);
}

double ClientDecryptScalar(
    const CryptoContext<DCRTPoly>& context,
    const lbcrypto::PrivateKey<DCRTPoly>& secret_key,
    const Ciphertext<DCRTPoly>& ciphertext) {
    Plaintext decrypted;
    context->Decrypt(secret_key, ciphertext, &decrypted);
    decrypted->SetLength(1);
    return decrypted->GetRealPackedValue().at(0);
}

double PlainWeightedSum() {
    double result = credit_risk::kBias;
    for (std::size_t index = 0; index < credit_risk::kFeatureCount; ++index) {
        result += credit_risk::kScaledFeatures[index] * credit_risk::kWeights[index];
    }
    return result;
}

void WriteReport(const VerificationResult& result, std::uint32_t ring_dimension) {
    const std::filesystem::path output_path =
        std::filesystem::path("benchmarks") / "results" / "day2_fhe_verification.json";
    std::filesystem::create_directories(output_path.parent_path());
    std::ofstream output(output_path);
    output << std::setprecision(17)
           << "{\n"
           << "  \"scheme\": \"CKKS\",\n"
           << "  \"openfhe_version\": \"1.5.1\",\n"
           << "  \"ring_dimension\": " << ring_dimension << ",\n"
           << "  \"feature_count\": " << credit_risk::kFeatureCount << ",\n"
           << "  \"plain_logit\": " << result.plain_logit << ",\n"
           << "  \"fhe_decrypted_logit\": " << result.fhe_logit << ",\n"
           << "  \"absolute_error\": " << result.absolute_error << ",\n"
           << "  \"relative_error\": " << result.relative_error << ",\n"
           << "  \"secret_key_available_to_server\": false,\n"
           << "  \"verified\": " << (result.absolute_error < 1e-6 ? "true" : "false") << "\n"
           << "}\n";
}

}  // namespace

int main() {
    try {
        std::cout << std::setprecision(17);
        auto context = CreateContext();
        auto client_keys = GenerateClientKeys(context);

        std::cout << "Phase 6: CKKS context created (ring dimension "
                  << context->GetRingDimension() << ")\n";
        std::cout << "Phase 7: public, secret, and evaluation keys generated\n";
        std::cout << "          secret key remains at the client boundary\n";

        auto encrypted_features = ClientEncryptFeatures(context, client_keys.key_pair.publicKey);
        std::cout << "Phase 8: encrypted " << encrypted_features.size()
                  << " scaled real-valued customer features\n";

        auto encrypted_logit = ServerWeightedSum(context, encrypted_features);
        std::cout << "Phase 9: server evaluated Enc(w dot x + b) without a secret key\n";

        const double fhe_logit = ClientDecryptScalar(context, client_keys.key_pair.secretKey, encrypted_logit);
        const double plain_logit = PlainWeightedSum();
        const double absolute_error = std::abs(plain_logit - fhe_logit);
        const double relative_error = absolute_error / std::max(std::abs(plain_logit), 1e-15);
        VerificationResult result{plain_logit, fhe_logit, absolute_error, relative_error};

        std::cout << "Phase 10 verification:\n"
                  << "  plaintext logit     = " << plain_logit << "\n"
                  << "  decrypted FHE logit = " << fhe_logit << "\n"
                  << "  absolute error      = " << absolute_error << "\n"
                  << "  relative error      = " << relative_error << "\n";

        if (std::abs(plain_logit - credit_risk::kExpectedPlainLogit) > 1e-12) {
            throw std::runtime_error("C++ plaintext logit does not match the exported Python logit");
        }
        WriteReport(result, context->GetRingDimension());
        if (absolute_error >= 1e-6) {
            throw std::runtime_error("CKKS error exceeded the Day 2 tolerance");
        }
        std::cout << "PASS: CKKS weighted sum matches plaintext within tolerance\n";
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
