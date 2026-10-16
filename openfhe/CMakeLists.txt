cmake_minimum_required(VERSION 3.16)
project(credit_risk_fhe LANGUAGES CXX)

set(OPENFHE_VERSION_STRING "1.5.1" CACHE STRING "Version of the pinned OpenFHE runtime")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

set(OPENFHE_LOCAL_PREFIX "${CMAKE_CURRENT_SOURCE_DIR}/install" CACHE PATH "OpenFHE installation prefix")

add_executable(day2_ckks src/day2_ckks.cpp)
add_executable(day3_fhe_predict src/day3_fhe_predict.cpp)
add_executable(fhe_protocol src/fhe_protocol.cpp)
target_include_directories(day2_ckks PRIVATE
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/third-party/include
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/core
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/pke
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/binfhe
    ${CMAKE_CURRENT_SOURCE_DIR}/generated
)
target_link_directories(day2_ckks PRIVATE ${OPENFHE_LOCAL_PREFIX}/lib)
target_link_libraries(day2_ckks PRIVATE OPENFHEpke OPENFHEcore)

target_include_directories(day3_fhe_predict PRIVATE
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/third-party/include
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/core
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/pke
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/binfhe
    ${CMAKE_CURRENT_SOURCE_DIR}/generated
)
target_link_directories(day3_fhe_predict PRIVATE ${OPENFHE_LOCAL_PREFIX}/lib)
target_link_libraries(day3_fhe_predict PRIVATE OPENFHEpke OPENFHEcore)

target_include_directories(fhe_protocol PRIVATE
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/third-party/include
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/core
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/pke
    ${OPENFHE_LOCAL_PREFIX}/include/openfhe/binfhe
    ${CMAKE_CURRENT_SOURCE_DIR}/generated
)
target_link_directories(fhe_protocol PRIVATE ${OPENFHE_LOCAL_PREFIX}/lib)
target_link_libraries(fhe_protocol PRIVATE OPENFHEpke OPENFHEcore)
target_compile_definitions(fhe_protocol PRIVATE OPENFHE_VERSION=${OPENFHE_VERSION_STRING})
