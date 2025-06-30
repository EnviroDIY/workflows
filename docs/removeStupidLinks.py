#!/usr/bin/env python
# %%
import re
import os

# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys() and "DOC_ROOT" in os.environ.keys():
    docbuild_dir = os.environ.get("DOC_ROOT")
    repo_name = os.environ.get("GITHUB_REPOSITORY").split("/")[1]
    relative_dir = f"../../../../{repo_name}_Doxygen/m.css/"
    relative_html = f"../../../../{repo_name}_Doxygen/html/"
else:
    docbuild_dir = os.getcwd()
    docbuild_dir = (
        "C:\\Users\\sdamiano\\Documents\\GitHub\\EnviroDIY\\ModularSensors\\docs"
    )
    repo_name = docbuild_dir.replace("\\\\", "/").replace("\\", "/").split("/")[-2]
    relative_dir = f"../../{repo_name}_Doxygen/m.css/"
    relative_html = f"../../{repo_name}_Doxygen/html/"

doxy_mcss_dir = os.path.join(docbuild_dir, relative_dir)
doxy_mcss_dir = os.path.abspath(os.path.realpath(doxy_mcss_dir))

doxy_html_dir = os.path.join(docbuild_dir, relative_html)
doxy_html_dir = os.path.abspath(os.path.realpath(doxy_html_dir))

print(f"Repository Name: {repo_name}")
print(f"Documentation Building Directory: {docbuild_dir}")
print("m.css HTML Directory: {}".format(doxy_mcss_dir))

search_files = []


def add_search_files(directory):
    """Add all files in the directory to the search_files list."""
    if os.path.isdir(directory):
        for root, _, files in os.walk(directory):
            for f in files:
                if (
                    f.endswith(".html")
                    and not f.endswith("fixed")
                    and not f.endswith("cleaned")
                    and not f.endswith("original")
                    and not f.endswith("_pre_cleaned")
                    and not f.startswith("_")
                    and not f.startswith("class_")
                    and not f.startswith("dir_")
                    and not f.startswith("group_")
                ):
                    search_files.append(os.path.join(root, f))


add_search_files(doxy_mcss_dir)
add_search_files(doxy_html_dir)

# %%
stupid_link_pattern = r'<a(?: class="(?:el|m-doc)")? href="(?P<stupid_link>\w+?)\.html"(?: class="(?:el|m-doc)")?>DELETE THIS LINK</a>'
for filename in search_files:
    abs_in = filename
    abs_out = filename + "_cleaned"
    copy_paste_needed = False

    print(f"Processing file: {filename}")

    with open(abs_in, "r", encoding="utf8") as in_file:  # open in readonly mode
        lines = in_file.readlines()
        i = 0

        new_lines = []
        for line in lines:
            i += 1
            # print(f"Processing line {i}: {line.strip()}")
            new_line = line
            match = re.search(
                stupid_link_pattern,
                new_line,
                flags=re.MULTILINE,
            )
            # remove the link
            new_line = re.sub(
                stupid_link_pattern,
                "",
                new_line,
                flags=re.MULTILINE,
            )
            # remove any left-over empty paragraphs
            new_line = re.sub(r"<p>\s*</p>", "", new_line, flags=re.MULTILINE)
            new_lines.append(new_line)
            # print the link that was removed
            if match is not None:
                copy_paste_needed = True
                print(f"\tRemoved link in line {i}: {match.group("stupid_link")}")

    if copy_paste_needed:
        with open(abs_out, "w+", encoding="utf8") as out_file:
            for line in new_lines:
                out_file.write(line)

        os.rename(
            os.path.join(doxy_mcss_dir, filename),
            os.path.join(doxy_mcss_dir, filename + "_pre_cleaned"),
        )
        os.rename(
            os.path.join(doxy_mcss_dir, filename + "_cleaned"),
            os.path.join(doxy_mcss_dir, filename),
        )

# %%
