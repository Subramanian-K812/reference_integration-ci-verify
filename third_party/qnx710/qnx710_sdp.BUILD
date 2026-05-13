package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all_files",
    srcs = glob(["**/*"]),
)

filegroup(
    name = "cxx_builtin_include_directories",
    srcs = [
        "host/linux/x86_64/usr/lib/gcc/aarch64-unknown-nto-qnx7.1.0/8.3.0/include",
        "target/qnx7/usr/include",
        "target/qnx7/usr/include/c++/v1",
    ],
)

filegroup(
    name = "ar",
    srcs = ["host/linux/x86_64/usr/bin/aarch64-unknown-nto-qnx7.1.0-ar"],
)

filegroup(
    name = "cc",
    srcs = ["host/linux/x86_64/usr/bin/qcc"],
)

filegroup(
    name = "cxx",
    srcs = ["host/linux/x86_64/usr/bin/q++"],
)

filegroup(
    name = "qcc",
    srcs = [":cc"],
)

filegroup(
    name = "qpp",
    srcs = [":cxx"],
)

filegroup(
    name = "strip",
    srcs = ["host/linux/x86_64/usr/bin/aarch64-unknown-nto-qnx7.1.0-strip"],
)

filegroup(
    name = "host_all",
    srcs = glob(["host/linux/x86_64/**/*"]),
)

filegroup(
    name = "host_dir",
    srcs = ["host/linux/x86_64"],
)

filegroup(
    name = "target_all",
    srcs = glob(["target/qnx7/**/*"]),
)

filegroup(
    name = "target_dir",
    srcs = ["target/qnx7"],
)

filegroup(
    name = "mkifs",
    srcs = ["host/linux/x86_64/usr/bin/mkifs"],
)
