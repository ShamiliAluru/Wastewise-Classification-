from __future__ import annotations

import streamlit as st

from src.catalog import CATEGORY_ORDER, CATEGORY_INFO, describe_text
from src.inference import classify_image, get_model_status
from src.ui import inject_styles, render_category_card, render_header, render_result

st.set_page_config(page_title="Wastewise — sort with confidence", page_icon="♻️", layout="wide", initial_sidebar_state="collapsed")
inject_styles()
render_header()

st.markdown('<div class="section-kicker">01 / YOUR ITEM</div>', unsafe_allow_html=True)
st.markdown('<h2 class="section-title">Show us what you’re sorting</h2>', unsafe_allow_html=True)
st.markdown('<p class="section-copy">A photo works best. You can also describe the item, or use both if the picture leaves out an important detail.</p>', unsafe_allow_html=True)

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    with st.container(border=True):
        st.markdown('<div class="input-heading"><span class="step-number">A</span><div><strong>Upload a photo</strong><small>One item, clear light, simple background</small></div></div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
        if uploaded:
            st.image(uploaded, use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown('<div class="input-heading"><span class="step-number">B</span><div><strong>Describe it</strong><small>Optional — useful for mixed or unclear items</small></div></div>', unsafe_allow_html=True)
        description = st.text_area("Item description", placeholder="For example: an empty glass pasta jar with a metal lid", height=142, label_visibility="collapsed", max_chars=300)
        st.caption("Tip: mention what it is made of, whether it is empty, and any labels or parts.")

_, action_col = st.columns([2.3, 1])
with action_col:
    check = st.button("Check this item  →", type="primary", use_container_width=True)

if check:
    if not uploaded and not description.strip():
        st.session_state.notice = "Add a photo or a short description to get started."
        st.session_state.result = None
    else:
        st.session_state.notice = None
        st.session_state.confirmed = False
        st.session_state.show_correction = False
        st.session_state.show_description_tip = False
        st.session_state.candidate_index = 0
        image_result = classify_image(uploaded.getvalue()) if uploaded else None
        if image_result and image_result.get("status") == "ready":
            st.session_state.result = {**image_result, "source": "image"}
        elif image_result and image_result.get("status") == "unknown" and description.strip():
            text_result = describe_text(description)
            if text_result.get("status") == "ready":
                st.session_state.result = {**text_result, "source": "text", "image_uncertain": True}
            else:
                st.session_state.result = {**image_result, "source": "image"}
        elif image_result and image_result.get("status") == "invalid" and description.strip():
            st.session_state.result = {**describe_text(description), "source": "text", "image_issue": True}
        elif image_result and image_result.get("status") == "invalid":
            st.session_state.result = {"status": "invalid", "source": "image", "detail": image_result.get("detail", "The image could not be opened.")}
        elif image_result and image_result.get("status") == "unavailable" and description.strip():
            st.session_state.result = {**describe_text(description), "source": "text", "image_unavailable": True}
        elif description.strip():
            st.session_state.result = {**describe_text(description), "source": "text"}
        else:
            st.session_state.result = {"status": "unavailable", "source": "image"}

if st.session_state.get("notice"):
    st.info(st.session_state.notice)

result = st.session_state.get("result")
if result:
    st.markdown('<div class="result-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">02 / YOUR SORTING GUIDE</div>', unsafe_allow_html=True)
    if result["status"] == "invalid":
        st.markdown('<div class="notice-card"><div class="notice-icon">↗</div><div><strong>We couldn’t read that image</strong><p>Try a brighter, closer photo with one item in view, or describe it in the box above.</p></div></div>', unsafe_allow_html=True)
        st.caption(result.get("detail", ""))
    elif result["status"] == "unavailable":
        st.markdown('<div class="notice-card"><div class="notice-icon">✦</div><div><strong>The image model isn’t ready yet</strong><p>Add a description for a helpful starter suggestion, or train the image model using the project guide.</p></div></div>', unsafe_allow_html=True)
    elif result["status"] == "unknown":
        candidates = result.get("candidates", [])
        if candidates:
            index = st.session_state.get("candidate_index", 0)
            if index < len(candidates):
                guess = candidates[index]
                st.markdown('<div class="notice-card"><div class="notice-icon">?</div><div><strong>Let’s identify the item</strong><p>A quick yes or no will help us choose the right guide.</p></div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="confirm-prompt">Is this {guess["item"]}?</div>', unsafe_allow_html=True)
                yes_col, no_col = st.columns(2)
                with yes_col:
                    if st.button("Yes", key=f"candidate_yes_{index}", type="primary", use_container_width=True):
                        st.session_state.result = {"status": "ready", **guess, "source": "image"}
                        st.session_state.confirmed = True
                        st.rerun()
                with no_col:
                    if st.button("No", key=f"candidate_no_{index}", use_container_width=True):
                        st.session_state.candidate_index = index + 1
                        st.rerun()
            else:
                st.markdown('<div class="followup-card"><strong>What is it made of?</strong><p>For example: plastic, paper, glass, metal, food, fabric, or a battery.</p></div>', unsafe_allow_html=True)
                clue = st.text_input("Describe the item or material", key="clarifying_material", placeholder="e.g. soft plastic wrapper")
                if st.button("Show my sorting guide", key="resolve_clue", type="primary"):
                    text_result = describe_text(clue)
                    if text_result["status"] == "ready":
                        st.session_state.result = {**text_result, "source": "text"}
                        st.session_state.confirmed = True
                        st.rerun()
                    st.warning("I still can’t identify that safely. Try naming the item or its main material.")
        else:
            st.markdown('<div class="notice-card"><div class="notice-icon">?</div><div><strong>What is the item made of?</strong><p>Tell us the item or material in a few words and we’ll match it to a sorting guide.</p></div></div>', unsafe_allow_html=True)
            clue = st.text_input("Item or material", key="unknown_material", placeholder="e.g. wet food scraps, glass jar, or old battery")
            if st.button("Show my sorting guide", key="resolve_unknown", type="primary"):
                text_result = describe_text(clue)
                if text_result["status"] == "ready":
                    st.session_state.result = {**text_result, "source": "text"}
                    st.session_state.confirmed = True
                    st.rerun()
                st.warning("I still can’t identify that safely. Try naming the item or its main material.")
    else:
        if result.get("image_uncertain"):
            st.info("The photo was unclear, so we used the item details you typed to make this suggestion.")
        if result.get("image_issue"):
            st.info("We couldn’t read the photo, so this suggestion is based on your description.")
        if result.get("image_unavailable"):
            st.info("The image model has not been trained yet, so this suggestion is based on your description.")
        category, item = result["category"], result.get("item", "this item")
        render_result(category, item, result.get("confidence"), result.get("source", "image"))
        if not st.session_state.get("confirmed") and result.get("source") == "text":
            st.caption("Based on the item details you entered. If this doesn’t match, edit the description above and check again.")
        st.markdown('<div class="section-kicker action-kicker">03 / NEXT STEPS</div>', unsafe_allow_html=True)
        render_category_card(category, item)

st.markdown('<div class="footer-note">Wastewise offers general sorting guidance. It cannot verify local collection rules, contamination, or every material blend. When an item may be hazardous, use the product label and an appropriate local collection service.</div>', unsafe_allow_html=True)
with st.expander("About this project"):
    if get_model_status()["ready"]:
        st.write("A fine-tuned image classifier is installed. Predictions are suggestions, and low-confidence results ask for human input.")
    else:
        st.write("The photo classifier is not installed yet. The description helper uses a small, transparent keyword guide; it is not an AI language model. Photo predictions will become available after training completes and the model files are added.")
    st.caption("Wastewise is an educational sorting assistant, not an official waste-disposal authority.")
