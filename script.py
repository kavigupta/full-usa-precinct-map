"""
Download VEST data from here and extract to the folder FOLDER:
https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/K7760H
Download the NYT west virginia file and put it into the folder FOLDER:
https://drive.google.com/drive/folders/15piNz7Q4lFKmR2IIC4y6W2Zs9Vg8WxSF
Download cb_2018_us_county_500k.zip and place it into folder FOLDER:
https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html
"""
FOLDER = "/home/kavi/Downloads/vest-dataverse-precincts"
import us
import zipfile
import tempfile
import geopandas
import pandas as pd
import numpy as np
import geopandas as gpd

import tqdm.notebook as tqdm


def load_kentucky_wiki():
    mains = {"Trump/PenceRepublican": "R", "Biden/HarrisDemocratic": "D"}
    [table] = [
        x
        for x in pd.read_html(
            "https://en.wikipedia.org/wiki/2020_United_States_presidential_election_in_Kentucky"
        )
        if "Trump/PenceRepublican" in str(x)
    ]
    table = table[[x for x in table if x[1] in {"Votes", "County"} and x[0] != "Total"]]
    table = table.set_index(list(table)[0])
    assert table.index[-1] == "Total"
    table = table[:-1]
    out = {}
    for name in mains:
        out[mains[name]] = table[name, "Votes"]
    out["O"] = table[[x for x in table if x[0] not in mains]].T.sum().T
    return pd.DataFrame(out)


def ky():
    counties = geopandas.read_file(f"{FOLDER}/cb_2018_us_county_500k.zip").to_crs(
        "epsg:4326"
    )
    counties = counties[["STATEFP", "COUNTYFP", "NAME", "geometry"]]
    counties = counties[counties.STATEFP == "21"].copy()
    out = {}
    ky = load_kentucky_wiki()
    ky = counties.NAME.apply(lambda x: ky.loc[x])
    for name in ky:
        out[name] = ky[name]
    out["geometry"] = counties.geometry
    return pd.DataFrame(out)


def wv():
    table = geopandas.read_file(f"{FOLDER}/West Virginia.geojson").to_crs("epsg:4326")
    out = {}
    out["D"] = table.votes_dem
    out["R"] = table.votes_rep
    out["O"] = table.votes_total - out["D"] - out["R"]
    out["geometry"] = table.geometry
    return pd.DataFrame(out)


def get(state):
    print(state)
    if state == us.states.KY:
        return ky()
    if state == us.states.WV:
        return wv()
    path = f"{FOLDER}/{state.abbr.lower()}_2020.zip"
    frame = geopandas.read_file(f"{path}").to_crs("epsg:4326")
    out = {}
    main_parties = {"G20PRERTRU": "R", "G20PREDBID": "D"}
    out.update({main_parties[k]: frame[k] for k in main_parties})
    out["O"] = (
        frame[[x for x in frame if x.startswith("G20PRE") and x not in main_parties]]
        .T.sum()
        .T
    )
    out["geometry"] = frame.geometry
    return pd.DataFrame(out)

def main():
    states = us.STATES + [us.states.DC]
    tables = []
    for state in tqdm.tqdm(states):
        table = get(state)
        table["state"] = table.R.apply(lambda x: state.abbr)
        tables.append(table)
    res = pd.concat(tables)
    gpd.GeoDataFrame(res).to_file("out/result.shp")

if __name__ == "__main__":
    main()