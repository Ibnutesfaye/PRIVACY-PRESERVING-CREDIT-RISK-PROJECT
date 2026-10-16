#include "openfhe.h"
#include "ciphertext-ser.h"
#include "cryptocontext-ser.h"
#include "key/key-ser.h"
#include "scheme/ckksrns/ckksrns-ser.h"
#include "model_input.h"
#include "polynomial_config.h"
#include "version.h"

#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using lbcrypto::Ciphertext;
using lbcrypto::CryptoContext;
using lbcrypto::CryptoContextCKKSRNS;
using lbcrypto::DCRTPoly;
using lbcrypto::GenCryptoContext;
using lbcrypto::Plaintext;

namespace {

constexpr std::size_t kBatchSize = 8192;
constexpr std::uint32_t kMultiplicativeDepth = 6;
constexpr std::uint32_t kScalingModulusBits = 50;
constexpr std::uint32_t kFirstModulusBits = 60;
constexpr auto kBinary = lbcrypto::SerType::BINARY;

void Require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

CryptoContext<DCRTPoly> CreateContext() {
    lbcrypto::CCParams<CryptoContextCKKSRNS> parameters;
    parameters.SetMultiplicativeDepth(kMultiplicativeDepth);
    parameters.SetScalingModSize(kScalingModulusBits);
    parameters.SetFirstModSize(kFirstModulusBits);
    parameters.SetBatchSize(kBatchSize);
    parameters.SetScalingTechnique(lbcrypto::FLEXIBLEAUTOEXT);
    parameters.SetKeySwitchTechnique(lbcrypto::HYBRID);
    parameters.SetSecurityLevel(lbcrypto::HEStd_128_classic);
    auto context = GenCryptoContext(parameters);
    context->Enable(lbcrypto::PKE);
    context->Enable(lbcrypto::KEYSWITCH);
    context->Enable(lbcrypto::LEVELEDSHE);
    return context;
}

CryptoContext<DCRTPoly> ReadContext(const std::filesystem::path& path) {
    CryptoContext<DCRTPoly> context;
    Require(lbcrypto::Serial::DeserializeFromFile(path.string(), context, kBinary), "Could not deserialize CKKS context");
    return context;
}

template <typename T>
T ReadObject(const std::filesystem::path& path, const std::string& label) {
    T value;
    Require(lbcrypto::Serial::DeserializeFromFile(path.string(), value, kBinary), "Could not deserialize " + label);
    return value;
}

template <typename T>
void WriteObject(const std::filesystem::path& path, const T& value, const std::string& label) {
    std::filesystem::create_directories(path.parent_path());
    Require(lbcrypto::Serial::SerializeToFile(path.string(), value, kBinary), "Could not serialize " + label);
}

std::vector<std::array<double, credit_risk::kFeatureCount>> ReadFeatures(const std::filesystem::path& path) {
    std::ifstream input(path);
    Require(static_cast<bool>(input), "Could not read scaled feature input");
    std::vector<std::array<double, credit_risk::kFeatureCount>> rows;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::stringstream stream(line);
        std::array<double, credit_risk::kFeatureCount> row{};
        std::string cell;
        for (std::size_t column = 0; column < row.size(); ++column) {
            Require(static_cast<bool>(std::getline(stream, cell, ',')), "Feature row must contain exactly seven values");
            row[column] = std::stod(cell);
        }
        Require(!std::getline(stream, cell, ','), "Feature row contains more than seven values");
        rows.push_back(row);
    }
    Require(!rows.empty() && rows.size() <= kBatchSize, "Batch size must be between 1 and 8192");
    return rows;
}

std::size_t ReadCount(const std::filesystem::path& directory) {
    std::ifstream input(directory / "batch.count");
    std::size_t count = 0;
    input >> count;
    Require(input.good() || input.eof(), "Could not read encrypted batch metadata");
    Require(count > 0 && count <= kBatchSize, "Encrypted batch count is invalid");
    return count;
}

Ciphertext<DCRTPoly> EvaluateLogit(const CryptoContext<DCRTPoly>& context, const std::vector<Ciphertext<DCRTPoly>>& features) {
    auto result = context->EvalMult(features[0], credit_risk::kWeights[0]);
    for (std::size_t index = 1; index < features.size(); ++index) {
        result = context->EvalAdd(result, context->EvalMult(features[index], credit_risk::kWeights[index]));
    }
    return context->EvalAdd(result, credit_risk::kBias);
}

Ciphertext<DCRTPoly> EvaluateSigmoid(const CryptoContext<DCRTPoly>& context, const Ciphertext<DCRTPoly>& z) {
    static_assert(credit_risk::kPolynomialDegree == 7, "Evaluator requires degree-7 polynomial");
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

void Setup(const std::filesystem::path& public_directory, const std::filesystem::path& private_directory) {
    auto context = CreateContext();
    auto keys = context->KeyGen();
    context->EvalMultKeyGen(keys.secretKey);
    WriteObject(public_directory / "context.bin", context, "CKKS context");
    WriteObject(public_directory / "public-key.bin", keys.publicKey, "public key");
    std::ofstream evaluation_keys(public_directory / "evaluation-mult-keys.bin", std::ios::binary);
    Require(static_cast<bool>(evaluation_keys), "Could not create evaluation-key file");
    Require(context->SerializeEvalMultKey(evaluation_keys, kBinary), "Could not serialize multiplication evaluation keys");
    WriteObject(private_directory / "secret-key.bin", keys.secretKey, "secret key");
    std::ofstream profile(public_directory / "profile.json");
    Require(static_cast<bool>(profile), "Could not create CKKS profile");
    profile << "{\n  \"protocol_version\": 1,\n  \"openfhe_version\": \"" << GetOPENFHEVersion()
            << "\",\n  \"scheme\": \"CKKS\",\n  \"feature_count\": 7,\n"
            << "  \"batch_capacity\": " << kBatchSize << ",\n  \"ring_dimension\": " << context->GetRingDimension()
            << ",\n  \"multiplicative_depth\": " << kMultiplicativeDepth
            << ",\n  \"scaling_modulus_bits\": " << kScalingModulusBits
            << ",\n  \"first_modulus_bits\": " << kFirstModulusBits
            << ",\n  \"scaling_technique\": \"FLEXIBLEAUTOEXT\""
            << ",\n  \"key_switch_technique\": \"HYBRID\""
            << ",\n  \"security_level\": \"HEStd_128_classic\""
            << ",\n  \"secret_key_in_public_bundle\": false\n}\n";
}

void Encrypt(const std::filesystem::path& context_path, const std::filesystem::path& public_key_path,
             const std::filesystem::path& input_path, const std::filesystem::path& output_directory) {
    auto context = ReadContext(context_path);
    auto public_key = ReadObject<lbcrypto::PublicKey<DCRTPoly>>(public_key_path, "public key");
    auto rows = ReadFeatures(input_path);
    std::filesystem::create_directories(output_directory);
    for (std::size_t column = 0; column < credit_risk::kFeatureCount; ++column) {
        std::vector<double> packed;
        for (const auto& row : rows) packed.push_back(row[column]);
        auto encrypted = context->Encrypt(public_key, context->MakeCKKSPackedPlaintext(packed));
        WriteObject(output_directory / ("feature-" + std::to_string(column) + ".ct"), encrypted, "feature ciphertext");
    }
    std::ofstream(output_directory / "batch.count") << rows.size() << '\n';
}

void Evaluate(const std::filesystem::path& context_path, const std::filesystem::path& evaluation_key_path,
              const std::filesystem::path& input_directory, const std::filesystem::path& result_path) {
    Require(!std::filesystem::exists(input_directory / "secret-key.bin"), "Evaluator input must not contain a secret key");
    auto context = ReadContext(context_path);
    std::ifstream evaluation_keys(evaluation_key_path, std::ios::binary);
    Require(static_cast<bool>(evaluation_keys), "Could not read multiplication evaluation keys");
    Require(context->DeserializeEvalMultKey(evaluation_keys, kBinary), "Could not deserialize multiplication evaluation keys");
    std::vector<Ciphertext<DCRTPoly>> features;
    for (std::size_t column = 0; column < credit_risk::kFeatureCount; ++column) {
        features.push_back(ReadObject<Ciphertext<DCRTPoly>>(input_directory / ("feature-" + std::to_string(column) + ".ct"), "feature ciphertext"));
    }
    (void)ReadCount(input_directory);
    WriteObject(result_path, EvaluateSigmoid(context, EvaluateLogit(context, features)), "result ciphertext");
}

void Decrypt(const std::filesystem::path& context_path, const std::filesystem::path& secret_key_path,
             const std::filesystem::path& result_path, std::size_t count, const std::filesystem::path& output_path) {
    Require(count > 0 && count <= kBatchSize, "Decryption count must be between 1 and 8192");
    auto context = ReadContext(context_path);
    auto secret_key = ReadObject<lbcrypto::PrivateKey<DCRTPoly>>(secret_key_path, "secret key");
    auto encrypted = ReadObject<Ciphertext<DCRTPoly>>(result_path, "result ciphertext");
    Plaintext plaintext;
    context->Decrypt(secret_key, encrypted, &plaintext);
    plaintext->SetLength(count);
    auto scores = plaintext->GetRealPackedValue();
    std::ofstream output(output_path);
    Require(static_cast<bool>(output), "Could not create decrypted-score output");
    output << std::setprecision(17);
    for (std::size_t index = 0; index < count; ++index) output << scores[index] << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        Require(argc >= 2, "Usage: fhe_protocol <setup|encrypt|evaluate|decrypt> ...");
        const std::string command = argv[1];
        if (command == "setup") {
            Require(argc == 4, "setup requires public-bundle and private-key directories");
            Setup(argv[2], argv[3]);
        } else if (command == "encrypt") {
            Require(argc == 6, "encrypt requires context, public key, scaled input, and output directory");
            Encrypt(argv[2], argv[3], argv[4], argv[5]);
        } else if (command == "evaluate") {
            Require(argc == 6, "evaluate requires context, evaluation keys, ciphertext directory, and result path");
            Evaluate(argv[2], argv[3], argv[4], argv[5]);
        } else if (command == "decrypt") {
            Require(argc == 7, "decrypt requires context, secret key, result, count, and output path");
            Decrypt(argv[2], argv[3], argv[4], std::stoull(argv[5]), argv[6]);
        } else {
            throw std::runtime_error("Unknown protocol command");
        }
        std::cout << "PASS: " << command << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
