#!/usr/bin/env python
# %%
import os
import xml.etree.ElementTree as ET
from slugify import slugify

# %%
# Some working directories

# The workspace directory
if "GITHUB_WORKSPACE" in os.environ.keys() and "DOC_ROOT" in os.environ.keys():
    docbuild_dir = os.environ.get("DOC_ROOT")
    repo_name = os.environ.get("GITHUB_REPOSITORY").split("/")[1]  # type: ignore
    relative_dir = f"../../../../{repo_name}_Doxygen/xml/"
else:
    docbuild_dir = os.getcwd()
    repo_name = docbuild_dir.replace("\\\\", "/").replace("\\", "/").split("/")[-2]
    relative_dir = f"../../{repo_name}_Doxygen/xml/"

# %%
doxy_xml_dir = os.path.join(docbuild_dir, relative_dir)  # type: ignore
doxy_xml_dir = os.path.abspath(os.path.realpath(doxy_xml_dir))

print(f"Repository Name: {repo_name}")
print(f"Documentation Building Directory: {docbuild_dir}")
print("XML Directory: {}".format(doxy_xml_dir))
print("-----\n\n\n")


# %%
def get_compound_id_and_location(root):
    """
    Get the compound id from the root of a Doxygen XML file.
    """
    compounddef = root.find("compounddef")
    if compounddef is not None:
        compound_id = compounddef.attrib.get("id")
        file_location = get_file_location(compounddef)
        return compound_id, file_location
    print("\tNo compounddef found in XML root")
    return None, None


def get_file_location(root):
    """
    Get the source file name from the root of a Doxygen XML file.
    """
    location = root.find("location")
    if location is not None:
        return location.attrib.get("file")
    print("\tNo location found in XML root")
    return None


def fix_bad_subsection_ids(root, compound_id, file_location):
    """
    Find and fix subsection ids that do not start with the compound id.
    This is a common issue in Doxygen XML files.
    """
    if compound_id is None or file_location is None:
        return False
    changes_made: bool = False
    for section_number in range(1, 7):
        for section in root.findall(f"sect{section_number}"):
            section_id = section.attrib.get("id")
            if not section_id.startswith(compound_id):
                print(
                    f"\tFixing section id: {section_id} to start with compound id: {compound_id}"
                )
                changes_made = True
                file_name_loc = section_id.find(file_location)
                section_suffix = section_id[file_name_loc + len(file_location) + 2 :]
                corrected_id = compound_id + "_" + section_suffix
                section.attrib["id"] = corrected_id
    return changes_made


def fix_bad_anchor_ids(root, compound_id):
    """
    Find and fix anchor ids that do not start with the compound id.
    This is a common issue in Doxygen XML files.
    """
    if compound_id is None:
        return False
    changes_made: bool = False
    for anchored_section in root.findall(".//anchor/../../.."):
        if (
            not anchored_section.tag == "sectiondef"
            or not anchored_section.attrib.get("kind") == "user-defined"
        ):
            continue
        header = anchored_section.find("header")
        if header is None or header.text is None:
            continue
        anchor = anchored_section.find(".//anchor")
        if anchor is not None:
            # print(f"\tChecking anchored section with header {header.text}")
            anchor_id = anchor.attrib.get("id")
            anchor_suffix = anchor_id.split("_1")[-1]
            header_slug = slugify(header.text, separator="_")
            if anchor_id != compound_id + "_1" + anchor_suffix:
                changes_made = True
                corrected_id = compound_id + "_1" + anchor_suffix
                print(
                    f"\tFixing anchor id: {anchor_id} to match compound and header: {corrected_id}"
                )
                anchor.attrib["id"] = corrected_id
    return changes_made


def remove_private_elements(root):
    """
    Remove any <memberdef>, <innerclass>, or <compounddef> elements with prot="private".
    """
    needs_to_be_fixed: bool = False
    removed_ids = []
    maybe_private_tags = ["memberdef", "innerclass", "compounddef"]
    for tag in maybe_private_tags:
        for parent in root.iter():
            to_remove = []
            for child in list(parent):
                if child.tag == tag and child.attrib.get("prot") == "private":
                    needs_to_be_fixed = True
                    id_tag = "refid" if tag == "innerclass" else "id"

                    removed_ids.append(child.attrib.get(id_tag))
                    if tag == "compounddef" and needs_to_be_fixed:
                        print(
                            f"\tWarning: To remove a private compounddef, you may need to remove the entire XML file for {child.attrib.get(id_tag)}"
                        )
                    else:
                        print(
                            f"\tRemoving private {child.tag} of type {child.attrib.get('kind')} with id {child.attrib.get(id_tag)}"
                        )
                        to_remove.append(child)
            for child in to_remove:
                parent.remove(child)

    return needs_to_be_fixed, removed_ids


def remove_private_sections(root):
    """
    Remove any <sectiondef> elements with kind="private-type", "private-func", or "private-attrib".
    """
    needs_to_be_fixed: bool = False
    # Remove any <sectiondef> elements with kind="private-type", "private-func", or "private-attrib".
    for parent in root.iter():
        to_remove = []
        for child in list(parent):
            if child.tag == "sectiondef" and child.attrib.get("kind") in [
                "private-type",
                "private-func",
                "private-attrib",
            ]:
                needs_to_be_fixed = True
                print(
                    f"\tRemoving private {child.tag} of type {child.attrib.get('kind')} with id {child.attrib.get('id')}"
                )
                to_remove.append(child)

        for child in to_remove:
            parent.remove(child)

    return needs_to_be_fixed


def remove_private_members_from_member_list(root):
    needs_to_be_fixed: bool = False
    # Iterate through all elements and remove matching members in the member list
    for parent in root.iter():
        # Make a list of children to remove
        to_remove = []
        for child in list(parent):
            if (
                parent.tag == "listofallmembers"
                and child.tag == "member"
                and child.attrib.get("prot") == "private"
            ):
                needs_to_be_fixed = True
                print(
                    f"\tRemoving private member from member list with name {child.find('name').text} and id {child.attrib.get('refid')}"
                )
                to_remove.append(child)

        for child in to_remove:
            parent.remove(child)

    return needs_to_be_fixed


def remove_private_members_from_index(root, ids_to_remove=[]):
    """
    Remove any <member> elements with prot="private" from the index.
    """
    needs_to_be_fixed: bool = False
    # Iterate through all elements and remove matching members in the member list
    for parent in root.iter():
        # Make a list of children to remove
        to_remove = []
        for child in list(parent):
            if child.tag == "member" and child.attrib.get("refid") in ids_to_remove:
                needs_to_be_fixed = True
                print(
                    f"\tRemoving private member from index with name {child.find('name').text}, kind {child.attrib.get('kind')}, and id {child.attrib.get('refid')}"
                )
                to_remove.append(child)

        for child in to_remove:
            parent.remove(child)

    return needs_to_be_fixed


# %%
def process_xml_file(filepath):
    """
    Load, clean, and save an XML file.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    needs_to_be_fixed: bool = False

    compound_id, file_location = get_compound_id_and_location(root)

    if compound_id is None and file_location is None:
        print(f"Skipping file {filepath} as it lacks compound_id and file_location.")
        return []

    needs_to_be_fixed |= fix_bad_subsection_ids(root, compound_id, file_location)
    needs_to_be_fixed |= fix_bad_anchor_ids(root, compound_id)
    has_private_elements, removed_ids = remove_private_elements(root)
    needs_to_be_fixed |= has_private_elements
    needs_to_be_fixed |= remove_private_sections(root)
    needs_to_be_fixed |= remove_private_members_from_member_list(root)

    if needs_to_be_fixed:
        print(
            f"File {filepath} has been modified to correct references and remove private members."
        )

        # Write back to the same file (or change to a new filename if preferred)
        # print(f"\tSaving new tree as {filepath.replace('.xml', '.xml_cleaned')}.")
        tree.write(
            filepath.replace(".xml", ".xml_cleaned"),
            encoding="utf-8",
            xml_declaration=True,
        )
        original_exists = os.path.exists(filepath + "_original")
        if not original_exists:
            os.rename(filepath, filepath + "_original")
        else:
            os.remove(filepath)
        os.rename(
            filepath + "_cleaned",
            filepath,
        )

    return removed_ids


def process_xml_index_file(filepath, removed_ids=[]):
    """
    Load, clean, and save an XML index file.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    if not filepath.endswith("index.xml"):
        print(f"Skipping file {filepath} as it is not an index.xml file.")
        return

    if len(removed_ids) == 0:
        print(f"Skipping file {filepath} as there are no private members to remove.")
        return

    needs_to_be_fixed = remove_private_members_from_index(
        root, ids_to_remove=removed_ids
    )

    if needs_to_be_fixed:
        print(f"Index file {filepath} has been modified to remove private members.")

        # Write back to the same file (or change to a new filename if preferred)
        tree.write(
            filepath.replace(".xml", ".xml_cleaned"),
            encoding="utf-8",
            xml_declaration=True,
        )
        original_exists = os.path.exists(filepath + "_original")
        if not original_exists:
            os.rename(filepath, filepath + "_original")
        else:
            os.remove(filepath)
        os.rename(
            filepath + "_cleaned",
            filepath,
        )


def process_directory(directory):
    """
    Scan all .xml files in a directory and process each one.
    """
    all_removed_ids = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(".xml") and not filename.lower().endswith(
            "index.xml"
        ):
            full_path = os.path.join(directory, filename)
            print(f"\n\nProcessing {full_path}")
            removed_ids = process_xml_file(filepath=full_path)
            all_removed_ids.extend(removed_ids)

    index_file = os.path.join(directory, "index.xml")
    if os.path.exists(index_file):
        process_xml_index_file(
            filepath=index_file,
            removed_ids=all_removed_ids,
        )


# %%
if __name__ == "__main__":
    # Change this to the directory you want to scan
    target_directory = doxy_xml_dir
    process_directory(directory=target_directory)

# %%
# cSpell:words compounddef sectiondef memberdef memberdefs refid listofallmembers innerclass refids
