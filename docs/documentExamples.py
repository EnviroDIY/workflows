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
    if (
        docbuild_dir.lower()
        == "c:\\users\\sdamiano\\documents\\github\\envirodiy\\workflows\\docs"
    ):
        docbuild_dir = (
            "C:\\Users\\sdamiano\\Documents\\GitHub\\EnviroDIY\\ModularSensors\\docs"
        )
    repo_name = docbuild_dir.replace("\\\\", "/").replace("\\", "/").split("/")[-2]
    relative_dir = f"../../{repo_name}/"

# %%
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
examples_to_doc = []
# Find all of the examples in the examples folder, append the path "examples" to it
if os.path.isdir(f"{examples_path}"):
    examples_to_doc += [
        os.path.abspath(
            os.path.realpath(f"{examples_path}/{example_dir}/{example_dir}.ino")
        )
        for example_dir in os.listdir(examples_path)
        if os.path.isdir(os.path.join(examples_path, example_dir))
        and os.path.isfile(
            os.path.abspath(
                os.path.realpath(f"{examples_path}/{example_dir}/{example_dir}.ino")
            )
        )
        and example_dir not in [".history", "logger_test", "menu_a_la_carte"]
    ]
# append any additional examples from the extras folder, iff it exists
if os.path.isdir(f"{extras_path}"):
    examples_to_doc += [
        os.path.abspath(os.path.realpath(f"{extras_path}/{extra_dir}/{extra_dir}.ino"))
        for extra_dir in os.listdir(extras_path)
        if os.path.isdir(os.path.join(extras_path, extra_dir))
        and os.path.isfile(
            os.path.abspath(
                os.path.realpath(f"{examples_path}/{extra_dir}/{extra_dir}.ino")
            )
        )
        and extra_dir not in [".history", "logger_test", "menu_a_la_carte"]
    ]
print("Examples to document:")
print("    ", end="")
print("\n    ".join(examples_to_doc))

# %%
with open(output_file, "w+") as out_file:
    for filename in examples_to_doc:
        if not os.path.isfile(filename):
            continue
        print(f"\nCurrent example: {filename}")
        with open(filename, "r") as in_file:  # open in readonly mode
            i = 1
            lines_copied = 0
            got_start_comment = False
            got_example_nav = False
            got_footer_nav = False
            lines = in_file.readlines()
            for line in lines:
                # remove any banners
                line = re.sub(r"^/\*\*\s*[=_-]+$", "/**", line)
                line = re.sub(r"^ *\*/\s*/\*\s*[=_-]+\s*\*/$", " */", line)
                line = re.sub(r"^ *\*\s*[=_-]+\s*\*/$", " */", line)
                # find start/end
                if i < 3 and line.startswith("/**"):
                    got_start_comment = True
                    print(f"  First line of doc block: {i}")
                if got_start_comment and "@m_examplenavigation" in line:
                    got_example_nav = True
                    print(f"  Got example nav command in line: {i}")
                if got_start_comment and "@m_footernavigation" in line:
                    got_footer_nav = True
                    print(f"  Got footer nav command in line: {i}")
                if got_start_comment and "*/" in line:
                    out_file.write(" *\n")
                    if not got_example_nav:
                        out_file.write(" * @m_examplenavigation{examples_page,}\n")
                    if not got_footer_nav:
                        out_file.write(" * @m_footernavigation\n")
                    end_comment_in_line = line.find("*/") + 2
                    out_file.write(line[0:end_comment_in_line])
                    print(f"  Last line of doc block: {i}")
                    # write out a directory listing for the example
                    out_file.write(f"\n/**\n * @dir {"/".join(filename.split(os.sep)[-3:-1])}\n * @brief Contains the {re.sub(r".ino$",'',os.path.split(filename)[1])} example.\n */\n")
                    got_start_comment = False
                    got_example_nav = False
                    got_footer_nav = False
                if got_start_comment:
                    out_file.write(line)
                    lines_copied += 1
                i += 1
            if lines_copied == 0:
                print(f"  No doc block detected in file")

            out_file.write("\n\n")


# %%
