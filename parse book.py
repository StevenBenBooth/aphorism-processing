"""This script processes Wood.txt into our csv format, and produces a plot of cumulative texts authored vs author ranking"""

import os
import re
import io

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from matplotlib.ticker import FormatStrFormatter

from custom_data import (
    shakespeare_aliases,
    auth_lang_map,
    auth_abbrev_map,
    origin_abbrev_map,
)

# Setup plot style

sns.set_style("darkgrid")
plt.rc("axes", labelsize=14)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=13)  # fontsize of the tick labels
plt.rc("ytick", labelsize=13)  # fontsize of the tick labels
plt.rc("legend", fontsize=13)  # legend fontsize
plt.rc("font", size=13)  # controls default text sizes


################## Preprocessing, converting txt to csv ########################


def format_output(original, translation, src_origin, src_info):
    if not src_info:
        src_info = None

    if translation:
        return (src_origin, original, translation, src_info)
    else:
        return (src_origin, None, original, src_info)


def refactor_src_info(src_info):
    res = src_info
    res = ". ".join(res)
    res = re.sub(r"\bPr.\b|\bPr\b|\bProv.\b|\bProv\b", "Proverb", res)
    res = re.sub(r"\bM.\b|\bM\b", "Maxim", res)
    return res


def process_entry(s):
    substitutions = [
        ("\d+", ""),
        ("\(\?\)", ""),
        ("\n", " "),
        (" {2,}", " "),
        ("_ _", " "),
        ("= \(.*?\).", "="),
        ("\(_lit._ .*?\)", ""),  # delete literal translations
    ]

    clean = s
    for pattern, repl in substitutions:
        clean = re.sub(pattern, repl, clean)

    # The most consistent structure is that sayings' source info
    # is in the last _..._ environment of the string
    reversed_src_info = re.findall("^.*?_.*?_", clean[::-1])

    src_info = None
    if reversed_src_info:
        src_info_string = reversed_src_info[0][::-1]  # put in correct direction

        # Delete source info from aphorism text
        clean = clean.replace(src_info_string, "").rstrip()
        src_info_string = src_info_string.rstrip()

        # We remove some details from the source information to reduce the
        # overall number of authors
        delete_conditions = [
            r",",
            r"'",
            r"\bto\b",
            r"\bTo\b",
            r"\bat\b",
            r"\bAt\b",
            r"\bon\b",
            r"\bOn\b",
            r"\bby\b",
            r"\bBy\b",
            r"\bin\b",
            r"\bIn\b",
            r"\bsaid\b",
            r"\bSaid\b",
            r"\bupon\b",
            r"\bUpon\b",
        ]

        # Remove elaborations in the source information
        for word in delete_conditions:
            pattern = "(" + word + ").*$"
            src_info_string = re.sub(pattern, "", src_info_string)

        src_info = [
            token.strip()
            for token in src_info_string.replace("_", "").split(".")
            if token.strip()
        ]

        # Replace any of the Shakespeare plays with "Shakespeare" as the source info
        if refactor_src_info(src_info) in shakespeare_aliases:
            src_info = ["Shakespeare"]

    # Translations from Greek have a special form
    greek_split = re.findall("\[Greek: (.*?)\]", clean)
    if greek_split:
        original = greek_split[0]
        translation = clean.replace("[Greek: {}]".format(original), "")

        assert translation[:2] == "--", "{} should start with an emdash".format(
            translation
        )
        translation = translation[2:].rstrip()
        if src_info:
            if src_info[0] == "Gr":
                # Already know it's greek, so Gr here is redundant
                src_info = src_info[1:]
            src_info = refactor_src_info(src_info)

        return original, translation, "Greek", src_info

    # Whenever the txt has an author aside, or a page break, it breaks out of
    # the source environment (enclosed by =), says what it needs to, then goes
    # back into the source environment with another =. Thus, we can extract only
    # the original saying's text by breaking the whole thing apart by '=', dropping
    # the spaces, and taking the even indexed chunks
    chunks = [chunk for chunk in clean.split("=") if chunk]
    original = " ".join(chunks[::2])

    # Translations sometimes contain "helpful" clarifications from the author
    # that we don't want, so we drop them here

    translation = clean.split("=")[-1]
    translation = re.sub(", _i.e._.*?$", "", translation)

    original = original.rstrip()
    translation = translation.rstrip()

    if translation:
        assert translation[:2] == "--", "{} should start with an emdash.".format(
            translation
        )
        translation = translation[2:]

    # Extract source origin
    src_origin = "UNK"
    if src_info:
        # Check if the source is an author's name
        try:
            author = refactor_src_info(src_info)
            src_origin = auth_lang_map[author]
            try:
                src_info = auth_abbrev_map[author]
            except KeyError:
                src_info = author

            return original, translation, src_origin, src_info

        except KeyError:
            pass

        # Law maxims have special form
        if src_info[0] in ["L", "Law"]:
            src_origin = "Latin"
            src_info[0] = "Law"

            return original, translation, src_origin, refactor_src_info(src_info)

        # Check if the first term is an origin abbreviation
        try:
            src_origin = origin_abbrev_map[src_info[0]]
            src_info = src_info[1:]

            return original, translation, src_origin, refactor_src_info(src_info)
        except KeyError:
            pass

        if src_info:
            src_info = refactor_src_info(src_info)
        else:
            src_info = None
    else:
        src_info = None

    if translation:
        # Translations with no source language are latin
        if src_origin == "UNK":
            src_origin = "Latin"

    return original, translation, src_origin, src_info


def process_Wood(path):
    """Function to process the semi-cleaned Wood text"""
    cleaned = []
    with io.open(path, "r", encoding="utf8") as file:
        lst = []
        for line in file:
            if line != "\n":
                lst.append(line)
            else:
                try:
                    to_add = format_output(*process_entry("".join(lst)))
                    cleaned.append(to_add)
                except IndexError as e:
                    print("IndexError: " + str(e))
                except AssertionError as e:
                    print("AssertionError: " + str(e))
                lst = []

        cleaned.append(
            format_output(*process_entry("".join(lst)))
        )  # include last entry
    return cleaned


BASE_PATH = os.path.join(os.getcwd(), "texts")
TEXT_PATH = os.path.join(BASE_PATH, "[Wood] Text.txt")

processed = process_Wood(TEXT_PATH)

df = pd.DataFrame(
    processed,
    columns=[
        "Aphorism Origin",
        "Original Text",
        "English Translation",
        "Source Information",
    ],
)

df.to_csv(
    os.path.join(os.getcwd(), "processed texts\\dataset.csv"),
    index=False,
)


############### Create log and record authorship information ###################
log_path = os.path.join(BASE_PATH, "log.txt")
author_info_path = os.path.join(BASE_PATH, "authors.txt")

authorset = dict()

with open(log_path, "w", encoding="utf8") as f:
    f.truncate(0)
    for val in processed:
        lang, original, translation, src = val
        if src:
            try:
                authorset[src] += 1
            except KeyError:
                authorset[src] = 1
        f.write(str(val) + "\n\n")


auth_counts = sorted(authorset.items(), key=lambda x: x[1], reverse=True)
with open(author_info_path, "w", encoding="utf8") as f:
    f.truncate(0)
    for name, count in auth_counts:
        f.write(str(name) + ": " + str(count) + "\n")

###################### Plotting author distribution curve ######################
# TODO: move this to EDA file; here is just more convenient since we already have `auth_counts`

# Process authorset to get a distribution curve
generic_auths = ["Proverb", "Maxim", "Anon", "Saying", "Quoted"]
generic_auth_counts = dict()
specific_auth_counts = dict()
i = 0
for name, count in auth_counts:
    if name in generic_auths:
        generic_auth_counts[i] = count
    else:
        specific_auth_counts[i] = count
    i += 1

total_docs = sum(authorset.values())


def cumulative_counts(counts):
    cum_count = 0
    for count in counts:
        cum_count += count
        yield cum_count


xs_gen, ys_gen = zip(*generic_auth_counts.items())
ys_gen = np.log10(np.array(ys_gen))

xs_spec, ys_spec = zip(*specific_auth_counts.items())

ys_cum_prop = [cum_count / total_docs for cum_count in cumulative_counts(ys_spec)]

ys_spec = np.log10(np.array(ys_spec))


max_log_count = np.log10(auth_counts[0][1])
num_auths = len(auth_counts)

fig, scatter_ax = plt.subplots()
line_ax = scatter_ax.twinx()

scatter_ax.set_xlim(-50, num_auths + 50)

buffer_prop = 0.1
scatter_ax.set_yticks(np.linspace(0, max_log_count, num=5))
line_ax.set_yticks(np.linspace(0, 1, num=5))

scatter_ax.set_ylim(-buffer_prop * max_log_count, (1 + buffer_prop) * max_log_count)
line_ax.set_ylim(-buffer_prop, 1 + buffer_prop)

scatter_ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
line_ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))

scatter_ax.set_xlabel("Author Rank")
scatter_ax.set_ylabel("Log Document Count")
line_ax.set_ylabel("Cumulative Prop. of Aphorisms\nby Informative Authors")


blue, orange, green, red = sns.color_palette("deep")[0:4]

scatter_ax.scatter(xs_spec, ys_spec, color=blue, label="Informative Author")
scatter_ax.scatter(xs_gen, ys_gen, color=red, label="Generic Author")
scatter_ax.legend()

line_ax.plot(xs_spec, ys_cum_prop, color=green)

plt.title("Authorship Distribution")
fig.tight_layout()
plt.show()
