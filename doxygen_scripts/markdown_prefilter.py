#!/usr/bin/env python
# %%
import fileinput
import re
import sys
import string
import hashlib
import argparse

# %%
# set up arg parse
try:
    get_ipython().__class__.__name__
    repo_name = "ModularSensors"
    input_file = "C:\\Users\\sdamiano\\Documents\\GitHub\\EnviroDIY\\ModularSensors\\examples\\ReadMe.md"
    local_testing = True
except NameError:
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file_positional", nargs="?")
    parser.add_argument(
        "--repo",
        type=str,
        default=argparse.SUPPRESS,
        help="The name of the repository, used to create and parse links to the GitHub repo.",
    )
    parser.add_argument(
        "--input_file",
        type=str,
        default=argparse.SUPPRESS,
        help="The name of the input file to process. If not provided, the script will read from standard input.",
    )
    args = parser.parse_args()
    repo_name = args.repo if "repo" in args else None
    input_file = args.input_file if "input_file" in args else args.input_file_positional
    local_testing = False


#  %%
# a helper function to go from snake back to camel
def snake_to_camel(snake_str: str) -> str:
    components = snake_str.replace("__", "_").strip().split("_")
    # in the case of multiple underscores, we want to keep the empty components
    components = ["_" if x == "" else x for x in components]
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    camel_str = components[0] + "".join(x.title() for x in components[1:])
    if camel_str.startswith("_"):
        return camel_str[1:]
    else:
        return camel_str


def camel_to_snake(name: str | None) -> str:
    if not name:
        return ""
    name = name.strip().replace(" ", "_")
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name.strip())
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def github_slugify(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace(
            "-", " "
        )  # convert dashes to spaces so they don't get lost with other punctuation
        .translate(str.maketrans("", "", string.punctuation))
        .replace("  ", " ")
        .replace("  ", " ")
        .replace(" ", "-")
    )


#  %%
# doxygen functions for converting file names
# functions are in https://github.com/doxygen/doxygen/blob/b3b06bddb788e48d207b286f00dbdc384a883ef2/src/util.cpp#L3841C1-L4069C2
# translated to python using https://www.codeconvert.ai/c++-to-python-converter


# this is used by doxygen to escape characters in the raw names of objects to be documented
def escape_chars_in_string(name: str, allow_dots: bool, allow_underscore: bool) -> str:
    if not name:
        return name

    case_sense_names = False  # Assuming case_sense_names is False for this
    allow_unicode_names = False  # Assuming allow_unicode_names is False for this
    grow_buf = []
    hex_chars = "0123456789abcdef"
    p = iter(name)

    for c in p:
        if c == "_":
            if allow_underscore:
                grow_buf.append("_")
            else:
                grow_buf.append("__")
        elif c == "-":
            grow_buf.append("-")
        elif c == ":":
            grow_buf.append("_1")
        elif c == "/":
            grow_buf.append("_2")
        elif c == "<":
            grow_buf.append("_3")
        elif c == ">":
            grow_buf.append("_4")
        elif c == "*":
            grow_buf.append("_5")
        elif c == "&":
            grow_buf.append("_6")
        elif c == "|":
            grow_buf.append("_7")
        elif c == ".":
            if allow_dots:
                grow_buf.append(".")
            else:
                grow_buf.append("_8")
        elif c == "!":
            grow_buf.append("_9")
        elif c == ",":
            grow_buf.append("_00")
        elif c == " ":
            grow_buf.append("_01")
        elif c == "{":
            grow_buf.append("_02")
        elif c == "}":
            grow_buf.append("_03")
        elif c == "?":
            grow_buf.append("_04")
        elif c == "^":
            grow_buf.append("_05")
        elif c == "%":
            grow_buf.append("_06")
        elif c == "(":
            grow_buf.append("_07")
        elif c == ")":
            grow_buf.append("_08")
        elif c == "+":
            grow_buf.append("_09")
        elif c == "=":
            grow_buf.append("_0a")
        elif c == "$":
            grow_buf.append("_0b")
        elif c == "\\":
            grow_buf.append("_0c")
        elif c == "@":
            grow_buf.append("_0d")
        elif c == "]":
            grow_buf.append("_0e")
        elif c == "[":
            grow_buf.append("_0f")
        elif c == "#":
            grow_buf.append("_0g")
        elif c == '"':
            grow_buf.append("_0h")
        elif c == "~":
            grow_buf.append("_0i")
        elif c == "'":
            grow_buf.append("_0j")
        elif c == ";":
            grow_buf.append("_0k")
        elif c == "`":
            grow_buf.append("_0l")
        else:
            if ord(c) < 0:
                do_escape = True
                if allow_unicode_names:
                    pass  # set to false for this script
                    # char_len = get_utf8_char_num_bytes(ord(c))
                    # if char_len > 0:
                    #     grow_buf.append(name[name.index(c) : name.index(c) + char_len])
                    #     next(p, None)  # Skip the next characters
                    #     do_escape = False
                if do_escape:
                    id = ord(c) & 0xFF
                    ids = f"_{hex_chars[id >> 4]}{hex_chars[id & 0xF]}"
                    grow_buf.append(ids)
            elif case_sense_names or not c.isupper():
                grow_buf.append(c)
            else:
                grow_buf.append("_")
                grow_buf.append(c.lower())

    return "".join(grow_buf)


# This is the inverse of escape_chars_in_string, used to unescape characters in strings
# It is used to convert the escaped names back to their original form.
def unescape_chars_in_string(s: str) -> str:
    if not s:
        return s
    case_sense_names = False  # Assuming case_sense_names is False for this
    result = []
    p = iter(s)

    try:
        while True:
            c = next(p)
            if c == "_":  # 2 or 3 character escape
                next_char = next(p)
                if next_char == "_":
                    result.append(c)  # __ -> '_'
                elif next_char == "1":
                    result.append(":")  # _1 -> ':'
                elif next_char == "2":
                    result.append("/")  # _2 -> '/'
                elif next_char == "3":
                    result.append("<")  # _3 -> '<'
                elif next_char == "4":
                    result.append(">")  # _4 -> '>'
                elif next_char == "5":
                    result.append("*")  # _5 -> '*'
                elif next_char == "6":
                    result.append("&")  # _6 -> '&'
                elif next_char == "7":
                    result.append("|")  # _7 -> '|'
                elif next_char == "8":
                    result.append(".")  # _8 -> '.'
                elif next_char == "9":
                    result.append("!")  # _9 -> '!'
                elif next_char == "0":  # 3 character escape
                    next_next_char = next(p)
                    if next_next_char == "0":
                        result.append(",")  # _00 -> ','
                    elif next_next_char == "1":
                        result.append(" ")  # _01 -> ' '
                    elif next_next_char == "2":
                        result.append("{")  # _02 -> '{'
                    elif next_next_char == "3":
                        result.append("}")  # _03 -> '}'
                    elif next_next_char == "4":
                        result.append("?")  # _04 -> '?'
                    elif next_next_char == "5":
                        result.append("^")  # _05 -> '^'
                    elif next_next_char == "6":
                        result.append("%")  # _06 -> '%'
                    elif next_next_char == "7":
                        result.append("(")  # _07 -> '('
                    elif next_next_char == "8":
                        result.append(")")  # _08 -> ')'
                    elif next_next_char == "9":
                        result.append("+")  # _09 -> '+'
                    elif next_next_char == "a":
                        result.append("=")  # _0a -> '='
                    elif next_next_char == "b":
                        result.append("$")  # _0b -> '$'
                    elif next_next_char == "c":
                        result.append("\\")  # _0c -> '\'
                    elif next_next_char == "d":
                        result.append("@")  # _0d -> '@'
                    elif next_next_char == "e":
                        result.append("]")  # _0e -> ']'
                    elif next_next_char == "f":
                        result.append("[")  # _0f -> '['
                    elif next_next_char == "g":
                        result.append("#")  # _0g -> '#'
                    elif next_next_char == "h":
                        result.append('"')  # _0h -> '"'
                    elif next_next_char == "i":
                        result.append("~")  # _0i -> '~'
                    elif next_next_char == "j":
                        result.append("'")  # _0j -> '\'
                    elif next_next_char == "k":
                        result.append(";")  # _0k -> ';'
                    elif next_next_char == "l":
                        result.append("`")  # _0l -> '`'
                    else:  # unknown escape, just pass underscore character as-is
                        result.append(c)
                        result.append(next_char)
                else:
                    if (
                        not case_sense_names and "a" <= next_char <= "z"
                    ):  # lower to upper case escape, _a -> 'A'
                        result.append(next_char.upper())
                    else:  # unknown escape, pass underscore character as-is
                        result.append(c)
                        result.append(next_char)
            else:  # normal character; pass as is
                result.append(c)
    except StopIteration:
        pass

    return "".join(result)


def MD5Buffer(data):
    return hashlib.md5(data.encode()).digest()


def MD5SigToString(md5_sig):
    return "".join(f"{byte:02x}" for byte in md5_sig)


# this is the inverse of convert_name_to_file, used to convert file names back to their original names.
# It is used to convert the escaped file names back to their original form.
# this is created by me, not copied from doxygen code
def convert_name_to_file(name, allowDots, allowUnderscore):
    if not name:
        return name

    shortNames = False  # Assuming shortNames is False for this
    createSubdirs = False  # Assuming createSubdirs is False for this
    result = ""

    if shortNames:  # use short names only
        pass  # only using long names in this script
    else:  # long names
        result = escape_chars_in_string(name, allowDots, allowUnderscore)
        resultLen = len(result)
        if resultLen >= 128:  # prevent names that cannot be created!
            md5_sig = MD5Buffer(result)
            sigStr = MD5SigToString(md5_sig)
            result = result[: 128 - 32] + sigStr

    if createSubdirs:
        pass  # not using subdirs in this script
    return result


# this is used by doxygen to convert the name of an object that will get its own documentation page into a file name for that object.
def convert_ref_to_name(escaped_ref: str) -> str:
    if not escaped_ref:
        return escaped_ref
    # these have been converted to md5 signatures, which cannot be converted back
    if len(escaped_ref) >= 128:
        return escaped_ref

    stripped_ref = escaped_ref

    # for some objects, doxygen adds a prefix to the name
    # strip those off here
    prefixes = ["module__", "group__", "dir_", "class", "namespace", "concept"]
    for prefix in prefixes:
        if stripped_ref.startswith(prefix):
            stripped_ref = stripped_ref[len(prefix) :]
    # in other cases, doxygen adds a post-fix to the name
    # strip those off here
    post_fixes = [
        "_dep_incl",
        "_incl",
        "_inherit_graph",
        "_coll_graph",
        "-members",
        "-example",
    ]
    for post_fix in post_fixes:
        if stripped_ref.endswith(post_fix):
            stripped_ref = stripped_ref[: -len(post_fix)]

    result = unescape_chars_in_string(stripped_ref)

    # when doxygen creates a link for a page, it uses exactly the text given in the @page command
    # so we do NOT want to unescape the characters in the name
    # unfortunately, we mostly have to guess what's a page
    # I *usually* prefix the generic page names with "page_" and the example names with "example_"
    # so I'm going to exclude those from the unescaping.
    known_pages = ["change_log", "example_", "extra_", "page_"]
    if any(escaped_ref.startswith(page) for page in known_pages):
        result = escaped_ref

    return result


# %%
print_me = True
skip_me = False
in_fence = False
fence_language = ""
i = 1


with fileinput.FileInput(
    input_file,
    openhook=fileinput.hook_encoded("utf-8", "surrogateescape"),
) as input:
    file_name = None
    change_log_version = ""
    for line in input:
        if input.isfirstline():
            # Get the file name and directory
            # We'll use this to create the section id comment
            file_name_dir = input.filename()
            if "\\" in file_name_dir:
                file_separator = "\\"
            else:
                file_separator = "/"
            if local_testing:
                print("Separator: '{}'\n".format(file_separator))
            file_dir = file_name_dir.rsplit(sep=file_separator, maxsplit=1)[0]
            file_name_ext = file_name_dir.rsplit(sep=file_separator, maxsplit=1)[1]
            file_name = file_name_ext.rsplit(sep=".", maxsplit=1)[0]
            file_ext = file_name_ext.rsplit(sep=".", maxsplit=1)[1]
            if local_testing:
                print(
                    "File Directory: {}, File Name: {}, File Extension: {}\n".format(
                        file_dir, file_name, file_ext
                    )
                )
            # For the example walk-throughs, written in the ReadMe files,
            # we want the example name, which is part of the directory.
            if "examples" in file_dir and file_name == "ReadMe":
                file_name = (
                    "example_" + file_dir.rsplit(sep=file_separator, maxsplit=1)[-1]
                )

        if local_testing:
            print(i, print_me, skip_me, in_fence, fence_language, line)

        # I'm using these comments to fence off content that is only intended for
        # github markdown rendering
        if "[//]: # ( Start GitHub Only )" in line:
            print_me = False

        # copy the original line to work with
        massaged_line = line
        # Convert markdown comment tags to c++/dox style comment tags
        massaged_line = re.sub(r"\[//\]: # \( @(\w+?.*) \)", r"@\1", massaged_line)
        # allow thank you tags
        massaged_line = massaged_line.replace("thanks to @", r"thanks to \@")
        massaged_line = massaged_line.replace("courtesy of @", r"courtesy of \@")
        markdown_header = re.match(
            r"(?P<heading_pounds>#{1,6})\s+(?P<section_name>[^<>\{\}\#]+)",
            massaged_line,
        )
        php_extra_header_label = re.search(r"\{#(.+)\}", massaged_line)
        anchor_header = re.search(
            r"<a name=\"(?P<section_anchor>\w+)\"></a>", massaged_line
        )

        # Add a PHP Markdown Extra style header id to the end of header sections that don't already have a header id.
        # use the GitHub anchor plus the file name as the section id.
        # GitHub anchors for headers are the text, stripped of punctuation,
        # with the spaces replaced by hyphens.
        if (
            file_name is not None
            and file_name != "ChangeLog"
            and markdown_header is not None
            and php_extra_header_label is None
            and anchor_header is None
        ):
            massaged_line = (
                markdown_header.group("heading_pounds")
                + " "
                + markdown_header.group("section_name").strip()
                + "  {#"
                + camel_to_snake(file_name)
                + "_"
                + github_slugify(markdown_header.group("section_name"))
                + "}\n"
            )

        # unhide existing PHP Markdown Extra header id's hiding in GitHub flavored markdown comments
        elif (
            file_name is not None
            and file_name != "ChangeLog"
            and markdown_header is not None
            and php_extra_header_label is not None
        ):
            massaged_line = re.sub(
                r"<!--!?\s*\{#(.+)\}\s*-->",
                r"{#\1}",
                massaged_line,
            )
            # if input.isfirstline():
            # else:
            #     massaged_line = (
            #         markdown_header.group("heading_pounds")
            #         + " "
            #         + markdown_header.group("section_name").strip()
            #         + "  {#"
            #         + camel_to_snake(file_name)
            #         + "_"
            #         + github_slugify(markdown_header.group("section_name"))
            #         + "}\n"
            #     )

        elif (
            file_name is not None
            and file_name != "ChangeLog"
            and markdown_header is not None
            and anchor_header is not None
        ):
            # convert anchors to section names
            massaged_line = re.sub(
                r"<a name=\"(?P<section_anchor>\w+)\"></a>",
                r"{#\g<section_anchor>}",
                massaged_line,
            )

        # Special work-around for the change log
        if file_name is not None and file_name == "ChangeLog":
            if line.lower().startswith("# changelog"):
                massaged_line = "# ChangeLog {#change_log}\n"
            version_re = re.match(
                r"#{2}\s+(?P<changelog_link>\[(?P<version_number>[^\{\}\#]+?)\])(?P<version_info>.*)",
                massaged_line,
            )
            version_action_re = re.match(
                r"#{3}\s+(?P<section_name>(?:Changed)|(?:Added)|(?:Removed)|(?:Fixed)|(?:Known Issues))",
                massaged_line,
            )
            if version_re is not None:
                change_log_version = (
                    version_re.group("version_number").strip().lower().replace(".", "-")
                )
                change_log_link = version_re.group("changelog_link")
                massaged_line = (
                    "@section "
                    + camel_to_snake(file_name)
                    + "_"
                    + change_log_version
                    + " "
                    + version_re.group("version_number")
                    + version_re.group("version_info")
                    + "\n"
                    + "GitHub Release: "
                    + change_log_link
                    # + "\n" #NOTE:  Adding the new line here would offset all doxygen line numbers
                )
            if version_action_re is not None:
                massaged_line = (
                    massaged_line.rstrip()
                    + "  {#"
                    + camel_to_snake(file_name)
                    + "_"
                    + change_log_version
                    + "_"
                    + camel_to_snake(version_action_re.group("section_name"))
                    + "}\n"
                )

        # convert internal hash-tag links to reference links
        internal_hash_link = re.search(
            r"\]\(#(?P<internal_anchor>[\w/-]+)\)",
            massaged_line,
        )
        if internal_hash_link is not None:
            massaged_line = re.sub(
                r"\]\(#(?P<internal_anchor>[\w/-]+)\)",
                "](@ref "
                + camel_to_snake(file_name)
                + "_"
                + github_slugify(internal_hash_link.group("internal_anchor"))
                + ")",
                massaged_line,
            )

        # convert hard-coded github.io links to reference links
        # I want these to be plain links, not reference links in the readme files, so they work nicely in GitHub
        # but I want them to be reference links in the doxygen files, so they work nicely in the doxygen html
        github_io_link = re.search(
            r"\]\(https://(?P<org_name>[\w-]+)\.github\.io/(?P<repo_name>[\w-]+)/(?P<file_name>[\w-]+)\.html\)",
            massaged_line,
        )
        if (
            github_io_link is not None
            and github_io_link.group("repo_name") is not None
            and github_io_link.group("repo_name") == repo_name
        ):
            slugged_ref = github_io_link.group("file_name")
            de_slugged_ref = convert_ref_to_name(slugged_ref)
            massaged_line = re.sub(
                r"\]\(https://(?P<org_name>[\w-]+)\.github\.io/(?P<repo_name>[\w-]+)/(?P<file_name>[\w-]+)\.html\)",
                "](@ref " + de_slugged_ref + ")",
                massaged_line,
            )

        # finally, replace code blocks with doxygen's preferred code block
        # also replace mermaid diagram blocks with pre/post tags
        # GitHub can render graphs in mermaid directly, but Doxygen needs extra tags and a script to do so.
        if "```" in line and not in_fence:
            in_fence = True
            language = re.search(r"```(?P<language>\w+)", massaged_line)
            if language is not None and language.group("language") == "mermaid":
                fence_language = "mermaid"
                massaged_line = massaged_line.replace(
                    "```mermaid", '<pre class="mermaid">'
                )
            elif language is not None:
                massaged_line = re.sub(
                    r"^```(?P<language>\w+)$", r"@code{\g<language>}", massaged_line
                )
                fence_language = language.group("language")
            else:
                massaged_line = massaged_line.replace("```", "@code")
                fence_language = ""
        elif "```" in line and in_fence:
            in_fence = False
            if fence_language == "mermaid":
                massaged_line = massaged_line.replace("```", "</pre>")
            else:
                massaged_line = massaged_line.replace("```", "@endcode")

        # hide lines that are not printed or skipped
        # write out an empty comment line to keep the line numbers identical
        if skip_me or not print_me:
            massaged_line = "<!--" + massaged_line.strip() + "-->\n"

        if (
            massaged_line.count("\n") != line.count("\n")
            or line.count("\n") != 1
            or massaged_line.count("\n") != 1
        ):
            raise Exception(
                '\n\nNot exactly one new lines\nFile:{}\nLine Number:{}\nNew Lines in Original: {}\nOriginal Line:\n"{}"\nNew Lines after Massage: {}\nMassaged Line:\n"{}"\n\n'.format(
                    input.filename(),
                    input.filelineno(),
                    line.count("\n"),
                    line,
                    massaged_line.count("\n"),
                    massaged_line,
                )
            )

        # write out the result
        try:
            sys.stdout.buffer.write(massaged_line.encode("utf-8"))
        except Exception as e:
            print(massaged_line, end="")

        # using skip_me to skip single lines, so unset it after reading a line
        if skip_me:
            skip_me = False

        # a page, section, subsection, or sub-subsection commands followed
        # immediately with by a markdown header leads to that section appearing
        # twice in the doxygen html table of contents.
        # I'm putting the section markers right above the header and then will skip the header.
        if re.match(r"\[//\]: # \( @mainpage", line) is not None:
            skip_me = True
        if re.match(r"\[//\]: # \( @page", line) is not None:
            skip_me = True
        if re.match(r"\[//\]: # \( @.*section", line) is not None:
            skip_me = True
        if re.match(r"\[//\]: # \( @paragraph", line) is not None:
            skip_me = True

        # I'm using these comments to fence off content that is only intended for
        # github markdown rendering
        if "[//]: # ( End GitHub Only )" in line:
            print_me = True

        i += 1

# %%
