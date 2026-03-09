cmake_minimum_required(VERSION 3.14)
project(asset-pack-dl VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find libcurl (required)
find_package(CURL REQUIRED)

add_executable(asset-pack-dl main.cpp)

target_link_libraries(asset-pack-dl PRIVATE CURL::libcurl)

target_compile_options(asset-pack-dl PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)

install(TARGETS asset-pack-dl DESTINATION bin)
