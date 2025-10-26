cmake_minimum_required(VERSION 4.0)
project(cmake-conan)
find_package(SDL3 REQUIRED)
add_executable(testprog main.c)
target_link_libraries(testprog PRIVATE SDL3::SDL3)

