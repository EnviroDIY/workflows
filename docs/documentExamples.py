#!/usr/bin/env python
import fileinput
import re
import os
import glob

# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys() and "DOC_ROOT" in os.environ.keys():
    docbuild_dir = os.environ.get("DOC_ROOT")
    repo_name = os.environ.get("GITHUB_REPOSITORY").split("/")[1]
    relative_dir = f"../../../../{repo_name}/"
else:
    docbuild_dir = os.getcwd()
    repo_name = docbuild_dir.replace("\\\\", "/").replace("\\", "/").split("/")[-2]
    relative_dir = f"../../{repo_name}/"

# where to write the file
output_file = relative_dir + "docs/examples.dox"
output_file = os.path.join(docbuild_dir, output_file)
output_file = os.path.abspath(os.path.realpath(output_file))

# The examples directory
examples_dir = relative_dir + "examples/"
examples_path = os.path.join(docbuild_dir, examples_dir)
examples_path = os.path.abspath(os.path.realpath(examples_path))

# The extras directory
extras_dir = relative_dir + "extras/"
extras_path = os.path.join(docbuild_dir, extras_dir)
extras_path = os.path.abspath(os.path.realpath(extras_path))

print(f"Repository Name: {repo_name}")
print(f"Documentation Building Directory: {docbuild_dir}")
print(f"Examples Path: {examples_path}")
print(f"Extras Path: {extras_path}")
print(f"DOX Output Path: {output_file}")


# %%
# Find all of the examples in the examples folder, append the path "examples" to it
examples_to_doc = [
    os.path.abspath(os.path.realpath(f"{examples_path}/{f}/{f}.ino"))
    for f in os.listdir(examples_path)
    if os.path.isdir(os.path.join(examples_path, f))
    and f not in [".history", "logger_test", "menu_a_la_carte"]
]
examples_to_doc += [
    os.path.abspath(os.path.realpath(f"{extras_path}/{f}/{f}.ino"))
    for f in os.listdir(extras_path)
    if os.path.isdir(os.path.join(extras_path, f))
    and f not in [".history", "logger_test", "menu_a_la_carte"]
]
print("Examples to document:")
print("    ", end="")
print("\n    ".join(examples_to_doc))

# %%
with open(output_file, "w+") as out_file:
    for filename in examples_to_doc:
        print(f"\nCurrent example: {filename}")
        with open(filename, "r") as in_file:  # open in readonly mode
            i = 1
            got_start_comment = False
            lines = in_file.readlines()
            for line in lines:
                if i < 3 and line.startswith("/**"):
                    got_start_comment = True
                    print(f"  First line of doc block: {i}")
                if got_start_comment and (
                    line.startswith("*/") or line.startswith(" */")
                ):
                    out_file.write(" *\n")
                    out_file.write(" * @m_examplenavigation{examples_page,}\n")
                    out_file.write(" * @m_footernavigation\n")
                    out_file.write(line)
                    print(f"  Last line of doc block: {i}")
                    got_start_comment = False
                if got_start_comment:
                    out_file.write(line)
                i += 1

            out_file.write("\n\n")


# %%