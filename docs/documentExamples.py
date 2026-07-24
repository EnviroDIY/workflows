#!/usr/bin/env python
import re
import os

# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys() and "DOC_ROOT" in os.environ.keys():
    docbuild_dir = os.environ.get("DOC_ROOT")
    repo_name = os.environ.get("GITHUB_REPOSITORY").split("/")[1]  # type: ignore
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
output_file = os.path.join(docbuild_dir, output_file)  # type: ignore
output_file = os.path.abspath(os.path.realpath(output_file))

# The examples directory
examples_dir = relative_dir + "examples/"
examples_path = os.path.join(docbuild_dir, examples_dir)  # type: ignore
examples_path = os.path.abspath(os.path.realpath(examples_path))

# The extras directory
extras_dir = relative_dir + "extras/"
extras_path = os.path.join(docbuild_dir, extras_dir)  # type: ignore
extras_path = os.path.abspath(os.path.realpath(extras_path))

print(f"Repository Name: {repo_name}")
print(f"Documentation Building Directory: {docbuild_dir}")
print(f"Examples Path: {examples_path}")
print(f"Extras Path: {extras_path}")
print(f"DOX Output Path: {output_file}")

# the file types that doxygen will parse
doxy_file_types = [
    r"c",
    r"cc",
    r"cxx",
    r"cpp",
    r"c++",
    r"h",
    r"hh",
    r"hxx",
    r"hpp",
    r"h++",
    r"tpp",
    r"inc",
    r"m",
    r"markdown",
    r"md",
    r"mm",
    r"dox",
    r"doc",
    r"txt",
]
doxy_file_type_patterns = (
    r"(?:(?:.*\." + r")\Z|(?:.*\.".join(doxy_file_types) + r"\Z))".replace(r"+", r"\\+")
)

# %%
examples_to_doc = []
# Find all of the examples in the examples folder, append the path "examples" to it
if os.path.isdir(f"{examples_path}"):
    for root, subdirs, files in os.walk(examples_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            if filename == os.path.split(root)[-1] + ".ino" and root not in [
                ".history",
                "logger_test",
                "archive",
                "tests",
                "menu_a_la_carte",
            ]:
                examples_to_doc.append(os.path.abspath(os.path.realpath(file_path)))
# append any additional examples from the extras folder, iff it exists
if os.path.isdir(f"{extras_path}"):
    for root, subdirs, files in os.walk(extras_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            if filename == os.path.split(root)[-1] + ".ino" and root not in [
                ".history",
                "logger_test",
                "archive",
                "tests",
                "menu_a_la_carte",
            ]:
                examples_to_doc.append(os.path.abspath(os.path.realpath(file_path)))
print("Examples to document:")
print("    ", end="")
print("\n    ".join(examples_to_doc))

# %% Find the primary examples page for example navigation
print("\nFinding primary examples page for example navigation...")
main_example_page = "examples_page"
if os.path.isdir(f"{examples_path}") and os.path.isfile(
    os.path.join(examples_path, "ReadMe.md")
):
    examples_page = os.path.abspath(
        os.path.realpath(os.path.join(examples_path, "ReadMe.md"))
    )
    with open(examples_page, "r") as in_file:  # open in readonly mode
        lines = in_file.readlines()
        got_example_page_tag = False
        for line in lines:
            i = 0
            if line.startswith("# "):
                page_tag = re.match(r"^# .*?<!--! {#(?P<page_name>.*)} -->$", line)
                if page_tag is not None:
                    main_example_page = page_tag.group("page_name")
                    print(
                        f"Got main example page name: {main_example_page} in line {i}"
                    )
                    got_example_page_tag = True
                break
            i += 1
        if not got_example_page_tag:
            print(
                f"Did not find main example page tag in {examples_page}, using default: {main_example_page}"
            )
else:
    print(
        f"Did not find {examples_path}ReadMe.md, using default main example page name: {main_example_page}"
    )

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
                        out_file.write(
                            f" * @m_examplenavigation{{{main_example_page},}}\n"
                        )
                    if not got_footer_nav:
                        out_file.write(" * @m_footernavigation\n")
                    end_comment_in_line = line.find("*/") + 2
                    out_file.write(line[0:end_comment_in_line])
                    print(f"  Last line of doc block: {i}")
                    # write out a directory listing for the example, only if there are other files in the directory
                    if (
                        len(
                            [
                                file
                                for file in os.listdir(os.path.dirname(filename))
                                if re.match(
                                    doxy_file_type_patterns, file, flags=re.IGNORECASE
                                )
                            ]
                        )
                        > 0
                    ):
                        print(f"  Writing directory listing for {filename}")
                        out_file.write(
                            f"\n/**\n * @dir {'/'.join(filename.split(os.sep)[-3:-1])}\n * @brief Contains the {re.sub(r'.ino$','',os.path.split(filename)[1])} example.\n */\n"
                        )
                    else:
                        print(f"  No directory listing needed for {filename}")
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
# cSpell:words examplenavigation
