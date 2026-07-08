"""MerchantScout -- Streamlit UI.

Same underlying pipeline (search -> enrich -> score -> rank), two renderings:
- BDR/SDR view: sortable call list.
- Field Rep view: map + downloadable route file.
"""
import pandas as pd
import streamlit as st

from core.angle import best_angle
from core.config import get_settings
from core.email_scraper import find_email
from core.exclude_list import add_excluded, load_excluded_ids
from core.geo_export import to_kml
from core.llm_writer import write_pitch_summary
from core.new_business import is_new_business
from core.places_client import search_merchants
from core.scoring import score_merchant
from core.tpv import estimate_revenue, estimate_tpv
from core.vertical_configs import list_verticals, load_vertical

st.set_page_config(page_title="MerchantScout", layout="wide")

st.title("MerchantScout")
st.caption(
    "Find, grade, and prioritize merchant prospects for POS and payment-processing outreach."
)

mode = st.sidebar.radio("View", ["BDR / SDR (call list)", "Field Rep (map & route)"])

with st.sidebar.form("search_form"):
    vertical_key = st.selectbox(
        "Vertical", list_verticals(), format_func=lambda k: load_vertical(k).name
    )
    location = st.text_input("Location", placeholder="Denver, CO or 80202")
    max_results = st.slider("Max results per business type", 5, 60, 20)
    fetch_emails = st.checkbox(
        "Look up emails (slower -- scrapes business websites)", value=True
    )
    submitted = st.form_submit_button("Find prospects")

if submitted:
    if not location.strip():
        st.error("Enter a location.")
        st.stop()

    try:
        settings = get_settings()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    vertical = load_vertical(vertical_key)
    excluded_ids = load_excluded_ids()

    all_places = {}
    with st.spinner("Searching Google Places..."):
        for place_type in vertical.google_place_types:
            query = f"{place_type.replace('_', ' ')} in {location}"
            try:
                found = search_merchants(
                    settings.google_places_api_key, query, None, max_results, settings.cache_ttl_hours
                )
            except Exception as e:
                st.warning(f"Search failed for '{query}': {e}")
                continue
            for place in found:
                if "id" in place:
                    all_places[place["id"]] = place

    rows = []
    with st.spinner(f"Scoring {len(all_places)} merchants..."):
        for place_id, place in all_places.items():
            if place_id in excluded_ids:
                continue

            revenue_est = estimate_revenue(place, vertical)
            tpv_est = estimate_tpv(revenue_est, vertical)
            new_biz, new_biz_note = is_new_business(place)
            score_result = score_merchant(place, vertical, new_biz)
            angle = best_angle(score_result.dominant_signal)
            pitch = write_pitch_summary(place, score_result.explanation, angle)

            email = find_email(place.get("websiteUri")) if fetch_emails else None

            loc = place.get("location", {})
            explanation = " | ".join(score_result.explanation)
            if new_biz_note:
                explanation += f" | {new_biz_note}"

            rows.append(
                {
                    "place_id": place_id,
                    "name": place.get("displayName", {}).get("text", "Unknown"),
                    "address": place.get("formattedAddress", ""),
                    "phone": place.get("internationalPhoneNumber", ""),
                    "email": email or "not found",
                    "website": place.get("websiteUri", ""),
                    "score": score_result.score,
                    "explanation": explanation,
                    "best_angle": pitch,
                    "est_monthly_tpv": round(tpv_est.monthly_tpv, 2),
                    "tpv_confidence": revenue_est.confidence,
                    "est_annual_revenue": round(revenue_est.annual_revenue, 2),
                    "rating": place.get("rating", ""),
                    "review_count": place.get("userRatingCount", 0),
                    "lat": loc.get("latitude"),
                    "lng": loc.get("longitude"),
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
    st.session_state["results"] = df
    st.session_state["last_vertical"] = vertical.name

df = st.session_state.get("results")

if df is not None and not df.empty:
    st.success(f"{len(df)} prospects found for {st.session_state.get('last_vertical', '')}")

    if mode == "BDR / SDR (call list)":
        display_cols = [
            "score", "name", "phone", "email", "address", "est_monthly_tpv",
            "tpv_confidence", "best_angle", "explanation", "website",
        ]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        selected_name = st.selectbox(
            "Mark a prospect as contacted (removes from future runs)",
            ["-"] + df["name"].tolist(),
        )
        if selected_name != "-" and st.button("Mark contacted"):
            row = df[df["name"] == selected_name].iloc[0]
            add_excluded(row["place_id"], row["name"])
            st.success(f"{selected_name} added to the exclude list.")

    else:  # Field Rep view
        map_df = df.dropna(subset=["lat", "lng"]).rename(
            columns={"lat": "latitude", "lng": "longitude"}
        )
        if not map_df.empty:
            st.map(map_df[["latitude", "longitude"]])
        else:
            st.info("No coordinates available for these results.")

        st.dataframe(
            df[["score", "name", "address", "phone", "best_angle", "est_monthly_tpv"]],
            use_container_width=True,
            hide_index=True,
        )

        kml = to_kml(df)
        st.download_button("Download route (KML for Google My Maps)", kml, file_name="route.kml")

    st.download_button(
        "Download full results (CSV)", df.to_csv(index=False), file_name="merchant_prospects.csv"
    )
elif df is not None:
    st.info("No prospects found (or all results are already on your exclude list). Try a different location or vertical.")
else:
    st.info("Fill out the form on the left and click 'Find prospects' to get started.")
