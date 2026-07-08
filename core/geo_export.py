"""Export ranked results for route planning (field-rep use case)."""
import pandas as pd


def to_kml(df: pd.DataFrame) -> str:
    placemarks = []
    for _, row in df.iterrows():
        lat, lng = row.get("lat"), row.get("lng")
        if pd.isna(lat) or pd.isna(lng):
            continue
        desc = f"Score: {row['score']} | {row.get('best_angle', '')}".replace("&", "and")
        name = str(row["name"]).replace("&", "and")
        placemarks.append(
            f"""
    <Placemark>
      <name>{name} (Score {row['score']})</name>
      <description>{desc}</description>
      <Point><coordinates>{lng},{lat},0</coordinates></Point>
    </Placemark>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>MerchantScout Route</name>{''.join(placemarks)}
  </Document>
</kml>"""
