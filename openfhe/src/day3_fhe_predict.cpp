#include "openfhe.h"
#include "ciphertext-ser.h"
#include "cryptocontext-ser.h"
#include "key/key-ser.h"
#include "scheme/ckksrns/ckksrns-ser.h"
#include "model_input.h"
#include "polynomial_config.h"

#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
using lbcrypto::Ciphertext;
using lbcrypto::CryptoContext;
using lbcrypto::CryptoContextCKKSRNS;
using lbcrypto::DCRTPoly;
using lbcrypto::GenCryptoContext;
using lbcrypto::Plaintext;

namespace {

constexpr std::size_t kBatchSize = 8192;

double Milliseconds(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

std::vector<std::array<double, credit_risk::kFeatureCount>> ReadFeatures(
    const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("Cannot open scaled-feature input file: " + path.string());
    }
    std::vector<std::array<double, credit_risk::kFeatureCount>> rows;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        std::array<double, credit_risk::kFeatureCount> row{};
        std::stringstream stream(line);
        std::string cell;
        for (std::size_t column = 0; column < credit_risk::kFeatureCount; ++column) {
            if (!std::getline(stream, cell, ',')) {
                throw std::runtime_error("Input row does not contain seven features");
            }
            row[column] = std::stod(cell);
        }
        rows.push_back(row);
    }
    if (rows.empty() || rows.size() > kBatchSize) {
        throw std::runtime_error("Input must contain between 1 and 8192 rows");
    }
    return rows;
}

CryptoContext<DCRTPoly> CreateContext() {
    lbcrypto::CCParams<CryptoContextCKKSRNS> parameters;
    // Weighted sum consumes one level. The degree-7 odd polynomial uses z^2,
    // z^3, z^5 and z^7 with a total circuit depth bounded by six.
    parameters.SetMultiplicativeDepth(6);
    parameters.SetScalingModSize(50);
    parameters.SetBatchSize(kBatchSize);
    auto context = GenCryptoContext(parameters);
    context->Enable(lbcrypto::PKE);
    context->Enable(lbcrypto::KEYSWITCH);
    context->Enable(lbcrypto::LEVELEDSHE);
    return context;
}

std::vector<Ciphertext<DCRTPoly>> ClientEncryptColumns(
    const CryptoContext<DCRTPoly>& context,
    const lbcrypto::PublicKey<DCRTPoly>& public_key,
    const std::vector<std::array<double, credit_risk::kFeatureCount>>& rows) {
    std::vector<Ciphertext<DCRTPoly>> encrypted;
    encrypted.reserve(credit_risk::kFeatureCount);
    for (std::size_t column = 0; column < credit_risk::kFeatureCount; ++column) {
        std::vector<double> packed;
        packed.reserve(rows.size());
        for (const auto& row : rows) {
            packed.push_back(row[column]);
        }
        encrypted.push_back(context->Encrypt(public_key, context->MakeCKKSPackedPlaintext(packed)));
    }
    return encrypted;
}

Ciphertext<DCRTPoly> ServerEncryptedLogit(
    const CryptoContext<DCRTPoly>& context,
    const std::vector<Ciphertext<DCRTPoly>>& features) {
    auto result = context->EvalMult(features[0], credit_risk::kWeights[0]);
    for (std::size_t index = 1; index < credit_risk::kFeatureCount; ++index) {
        result = context->EvalAdd(result, context->EvalMult(features[index], credit_risk::kWeights[index]));
    }
    return context->EvalAdd(result, credit_risk::kBias);
}

Ciphertext<DCRTPoly> ServerPolynomialSigmoid(
    const CryptoContext<DCRTPoly>& context,
    const Ciphertext<DCRTPoly>& z) {
    static_assert(credit_risk::kPolynomialDegree == 7, "Day 3 circuit expects the selected degree-7 polynomial");
    const auto& c = credit_risk::kSigmoidCoefficients;
    auto z2 = context->EvalMult(z, z);
    auto z3 = context->EvalMult(z2, z);
    auto z5 = context->EvalMult(z3, z2);
    auto z7 = context->EvalMult(z5, z2);

    auto result = context->EvalAdd(context->EvalMult(z, c[1]), c[0]);
    result = context->EvalAdd(result, context->EvalMult(z3, c[3]));
    result = context->EvalAdd(result, context->EvalMult(z5, c[5]));
    return context->EvalAdd(result, context->EvalMult(z7, c[7]));
}

std::uintmax_t SerializedCiphertextSize(const Ciphertext<DCRTPoly>& ciphertext) {
    const auto path = std::filesystem::path("benchmarks") / "results" / "ciphertext-size.tmp";
    std::filesystem::create_directories(path.parent_path());
    if (!lbcrypto::Serial::SerializeToFile(path.string(), ciphertext, lbcrypto::SerType::BINARY)) {
        throw std::runtime_error("Could not serialize ciphertext for size measurement");
    }
    const auto size = std::filesystem::file_size(path);
    std::filesystem::remove(path);
    return size;
}

void WriteScores(const std::filesystem::path& path, const std::vector<double>& scores, std::size_t count) {
    std::ofstream output(path);
    output << std::setprecision(17);
    for (std::size_t index = 0; index < count; ++index) {
        output << scores[index] << '\n';
    }
}

void WriteBenchmark(
    const std::filesystem::path& path,
    std::size_t samples,
    std::uint32_t ring_dimension,
    double keygen_ms,
    double encryption_ms,
    double evaluation_ms,
    double decryption_ms,
    double total_ms,
    std::uintmax_t ciphertext_bytes) {
    std::ofstream output(path);
    output << std::setprecision(17)
           << "{\n"
           << "  \"scheme\": \"CKKS\",\n"
           << "  \"polynomial_degree\": " << credit_risk::kPolynomialDegree << ",\n"
           << "  \"samples_packed\": " << samples << ",\n"
           << "  \"ring_dimension\": " << ring_dimension << ",\n"
           << "  \"key_generation_ms\": " << keygen_ms << ",\n"
           << "  \"encryption_ms\": " << encryption_ms << ",\n"
           << "  \"evaluation_ms\": " << evaluation_ms << ",\n"
           << "  \"decryption_ms\": " << decryption_ms << ",\n"
           << "  \"total_latency_ms\": " << total_ms << ",\n"
           << "  \"one_input_ciphertext_bytes\": " << ciphertext_bytes << ",\n"
           << "  \"seven_input_ciphertexts_bytes\": " << ciphertext_bytes * credit_risk::kFeatureCount << ",\n"
           << "  \"server_receives_plaintext_features\": false\n"
           << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const std::filesystem::path input = argc > 1 ? argv[1] : "openfhe/generated/fhe_test_batch.csv";
        const std::filesystem::path scores_path = argc > 2 ? argv[2] : "benchmarks/results/fhe_probabilities.csv";
        const std::filesystem::path benchmark_path = argc > 3 ? argv[3] : "benchmarks/results/fhe_timing.json";
        std::filesystem::create_directories(scores_path.parent_path());
        std::filesystem::create_directories(benchmark_path.parent_path());

        const auto total_start = Clock::now();
        const auto rows = ReadFeatures(input);
        auto context = CreateContext();

        const auto keygen_start = Clock::now();
        auto keys = context->KeyGen();
        context->EvalMultKeyGen(keys.secretKey);
        const auto keygen_end = Clock::now();

        const auto encryption_start = Clock::now();
        auto encrypted_features = ClientEncryptColumns(context, keys.publicKey, rows);
        const auto encryption_end = Clock::now();
        const auto ciphertext_bytes = SerializedCiphertextSize(encrypted_features.front());

        // SERVER: encrypted features enter here. No secret key is passed.
        const auto evaluation_start = Clock::now();
        auto encrypted_logit = ServerEncryptedLogit(context, encrypted_features);
        auto encrypted_probability = ServerPolynomialSigmoid(context, encrypted_logit);
        const auto evaluation_end = Clock::now();

        // CLIENT: only the client-held secret key decrypts the encrypted score.
        const auto decryption_start = Clock::now();
        Plaintext decrypted;
        context->Decrypt(keys.secretKey, encrypted_probability, &decrypted);
        decrypted->SetLength(rows.size());
        auto scores = decrypted->GetRealPackedValue();
        const auto decryption_end = Clock::now();
        const auto total_end = Clock::now();

        WriteScores(scores_path, scores, rows.size());
        WriteBenchmark(
            benchmark_path,
            rows.size(),
            context->GetRingDimension(),
            Milliseconds(keygen_start, keygen_end),
            Milliseconds(encryption_start, encryption_end),
            Milliseconds(evaluation_start, evaluation_end),
            Milliseconds(decryption_start, decryption_end),
            Milliseconds(total_start, total_end),
            ciphertext_bytes);

        std::cout << "PASS: evaluated " << rows.size()
                  << " packed encrypted predictions with degree-7 sigmoid approximation\n";
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
