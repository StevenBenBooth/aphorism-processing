import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# Setup plot style

sns.set_style("darkgrid")
plt.rc("axes", labelsize=14)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=13)  # fontsize of the tick labels
plt.rc("ytick", labelsize=13)  # fontsize of the tick labels
plt.rc("legend", fontsize=13)  # legend fontsize
plt.rc("font", size=13)  # controls default text sizes


df = pd.read_csv(os.path.join(os.getcwd(), "processed texts", "dataset.csv"))

print(df.describe(include="all"))

lang_counts = df["Aphorism Origin"].value_counts()


def aggregate_infreq_lang(lang_counts, other_cutoff=0.02):
    total_count = lang_counts.sum()
    assert total_count > 0, "total_count should be nonzero"
    lang_freqs = lang_counts / total_count

    # Aggregate "other" row
    small_rows = lang_freqs[lang_freqs <= other_cutoff]
    lang_freqs.drop(small_rows.index, inplace=True)
    lang_freqs.at["Other"] = small_rows.sum()

    return lang_freqs, small_rows


main_langs, infreq_langs = aggregate_infreq_lang(lang_counts)

explode = np.zeros(len(main_langs))
explode[-1] = 0.1

plot = main_langs.plot.pie(
    y=0,
    title="Aphorism Origins",
    legend=False,
    autopct="%.0f%%",
    colors=sns.color_palette("deep"),
    explode=explode,
    pctdistance=0.7,
    # shadow=True,
    startangle=0,
)

plt.axis("off")
plt.show()

print(infreq_langs)
