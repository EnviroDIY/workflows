#!/usr/bin/env python
# %%
import fileinput
import re
import os
import glob
import xml.etree.ElementTree as ET

# %%
# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys() and "DOC_ROOT" in os.environ.keys():
    docbuild_dir = os.environ.get("DOC_ROOT")
    repo_name = os.environ.get("GITHUB_REPOSITORY").split("/")[1]
    relative_dir = f"../../../../{repo_name}_Doxygen/xml/"
else:
    docbuild_dir = os.getcwd()
    repo_name = docbuild_dir.split("/")[-1]
    relative_dir = f"../{repo_name}_Doxygen/xml/"

doxy_xml_dir = os.path.join(docbuild_dir, relative_dir)
doxy_xml_dir = os.path.abspath(os.path.realpath(doxy_xml_dir))

print(f"Repository Name: {repo_name}")
print(f"Documentation Building Directory: {docbuild_dir}")
print("XML Directory: {}".format(doxy_xml_dir))

all_group_files = [
    f
    for f in os.listdir(doxy_xml_dir)
    if os.path.isfile(os.path.join(doxy_xml_dir, f))
    and f.startswith("group")
    and not f.endswith("fixed")
]

# %%
for filename in all_group_files:
    abs_in = os.path.join(doxy_xml_dir, filename)
    abs_out = os.path.join(doxy_xml_dir, filename + "_fixed")
    print("{}".format(abs_in))
    # print("out: {}".format(abs_out))
    # with open(output_file, 'w+') as out_file:
    with open(abs_out, "w+") as out_file:
        with open(abs_in, "r") as in_file:  # open in readonly mode
            lines = in_file.readlines()
            for line in lines:
                new_line = line
                new_line = new_line.replace("&lt;mcss:", "<mcss:")
                new_line = new_line.replace(
                    "&quot;http://mcss.mosra.cz/doxygen/&quot;",
                    '"http://mcss.mosra.cz/doxygen/"',
                )
                new_line = new_line.replace("&lt;/mcss:span&gt;", "</mcss:span>")
                new_line = new_line.replace("&lt;/span&gt;", "</span>")
                new_line = new_line.replace(
                    "mcss:class=&quot;m-dim&quot;&gt;", 'mcss:class="m-dim">'
                )
                new_line = new_line.replace(
                    "class=&quot;m-dim&quot;&gt;", 'class="m-dim">'
                )
                new_line = new_line.replace(
                    "mcss:class=&quot;m-param&quot;&gt;", 'mcss:class="m-param">'
                )
                new_line = new_line.replace(
                    "class=&quot;m-param&quot;&gt;", 'class="m-param">'
                )
                new_line = new_line.replace(
                    "mcss:class=&quot;m-doc-wrap&quot;&gt;", 'mcss:class="m-doc-wrap">'
                )
                new_line = new_line.replace(
                    "class=&quot;m-doc-wrap&quot;&gt;", 'class="m-doc-wrap">'
                )
                new_line = new_line.replace("&lt;span", "<span")
                # new_line = new_line.replace("&lt;mcss:", "<mcss:")
                # new_line = new_line.replace("&lt;mcss:", "<mcss:")
                # new_line = new_line.replace("&lt;mcss:", "<mcss:")
                # new_line = new_line.replace("&lt;mcss:", "<mcss:")
                # new_line = new_line.replace("&lt;mcss:", "<mcss:")
                # new_line = new_line.replace("&lt;mcss:", "<mcss:")
                new_line = new_line.replace(
                    '<parameterlist kind="param">',
                    '<mcss:class xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="m-table m-fullwidth m-flat"/>\n<table rows="3" cols="2"><row><entry thead="yes" colspan="2"><para>Parameters</para></entry></row>',
                )
                new_line = new_line.replace("</parameterlist>", "</table>")

                new_line = new_line.replace("<parameteritem>", "<row>")
                new_line = new_line.replace("</parameteritem>", "</row>")

                new_line = new_line.replace("<parameternamelist>\n", "")
                new_line = new_line.replace("</parameternamelist>\n", "")

                new_line = new_line.replace(
                    "<parametername>",
                    '<entry thead="no"><mcss:span xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="m-param">',
                )
                new_line = new_line.replace("</parametername>", "</mcss:span></entry>")

                new_line = new_line.replace(
                    "<parameterdescription>", '<entry thead="no">'
                )
                new_line = new_line.replace("</parameterdescription>", "</entry>")

                out_file.write(new_line)

    os.rename(
        os.path.join(doxy_xml_dir, filename),
        os.path.join(doxy_xml_dir, filename + "_original"),
    )
    os.rename(
        os.path.join(doxy_xml_dir, filename + "_fixed"),
        os.path.join(doxy_xml_dir, filename),
    )

# %%
