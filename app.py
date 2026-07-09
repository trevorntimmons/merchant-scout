"""MerchantScout -- Streamlit UI.

Same underlying pipeline (search -> enrich -> score -> rank), two renderings:
- BDR/SDR view: sortable call list.
- Field Rep view: map + downloadable route file.
"""
import math

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


def _haversine_miles(lat1, lng1, lat2, lng2):
    """Great-circle distance in miles between two lat/lng points."""
    r = 3958.8  # Earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


st.title("MerchantScout")
st.caption(
    "Find, grade, and prioritize merchant prospects for POS and payment-processing outreach."
)

with st.expander("How merchants are scored", expanded=False):
    st.markdown(
        "**Every merchant starts at a baseline of 10**, then earns points for "
        "buying-intent signals. The score measures *how urgent an opportunity* a "
        "merchant is — not how big the business is."
    )
    st.table({
        "Signal": [
            "Baseline",
            "No website found",
            "Payment-friction in reviews",
            "Competitor POS named in reviews",
            "Below-average rating (+ volume)",
            "Newly opened business",
        ],
        "Points": ["10", "+20", "+7 to +20", "+10", "+10", "+25"],
        "Why it matters": [
            "Starting floor — no merchant scores below this",
            "Likely no online ordering/payment presence yet",
            "Customers mention checkout pain — a live angle to lead with",
            "Reveals current setup — a conversation starter, not a confirmed contract",
            "Rating under 3.5 with 20+ reviews — operational friction proxy",
            "Registry match or first review within 12 months — still shopping",
        ],
    })
    st.caption(
        "Scores are additive and capped at 100. A low score isn't a bad business — "
        "it means the merchant shows no urgent switching signals right now."
    )

mode = st.sidebar.radio("View", ["BDR / SDR (call list)", "Field Rep (map & route)"])

with st.sidebar.form("search_form"):
    vertical_key = st.selectbox(
        "Vertical", list_verticals(), format_func=lambda k: load_vertical(k).name
    )
    location = st.text_input("Location", placeholder="Denver, CO or 80202")
    radius_miles = st.slider("Radius from location (miles)", 1, 35, 15)
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

    # --- Radius filter (Option 2: post-filter by distance from result center) ---
    if not df.empty:
        geo = df.dropna(subset=["lat", "lng"])
        if not geo.empty:
            center_lat = geo["lat"].mean()
            center_lng = geo["lng"].mean()
            df["distance_mi"] = df.apply(
                lambda r: _haversine_miles(center_lat, center_lng, r["lat"], r["lng"])
                if pd.notna(r["lat"]) and pd.notna(r["lng"]) else None,
                axis=1,
            )
            before = len(df)
            df = df[(df["distance_mi"].isna()) | (df["distance_mi"] <= radius_miles)]
            dropped = before - len(df)
            if dropped:
                st.session_state["radius_note"] = (
                    f"Radius filter: kept merchants within {radius_miles} mi of the "
                    f"search center, dropped {dropped} outside it."
                )
            else:
                st.session_state["radius_note"] = ""

    if not df.empty:
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
    st.session_state["results"] = df
    st.session_state["last_vertical"] = vertical.name

df = st.session_state.get("results")

if df is not None and not df.empty:
    st.success(f"{len(df)} prospects found for {st.session_state.get('last_vertical', '')}")
    radius_note = st.session_state.get("radius_note", "")
    if radius_note:
        st.caption(radius_note)

    if mode == "BDR / SDR (call list)":
        display_cols = [
            "score", "name", "phone", "email", "address", "distance_mi", "est_monthly_tpv",
            "tpv_confidence", "best_angle", "explanation", "website",
        ]
        display_cols = [c for c in display_cols if c in df.columns]
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

        rep_cols = [c for c in ["score", "name", "address", "phone", "distance_mi", "best_angle", "est_monthly_tpv"] if c in df.columns]
        st.dataframe(df[rep_cols], use_container_width=True, hide_index=True)

        kml = to_kml(df)
        st.download_button("Download route (KML for Google My Maps)", kml, file_name="route.kml")

    st.download_button(
        "Download full results (CSV)", df.to_csv(index=False), file_name="merchant_prospects.csv"
    )
elif df is not None:
    st.info("No prospects found (or all results are already on your exclude list). Try a different location or vertical.")
else:
    st.info("Fill out the form on the left and click 'Find prospects' to get started.")
