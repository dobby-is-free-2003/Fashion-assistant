"""Run: streamlit run app/app.py"""
import sys
import uuid
from pathlib import Path
from typing import get_args

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import streamlit as st  # noqa: E402

from fashion import config, db, demo, pipeline, privacy, stylist, trends, tryon, vectors  # noqa: E402
from fashion.rules import FAMILIES  # noqa: E402
from fashion.schema import ItemTags, Kind, Pattern  # noqa: E402
from fashion.service import StylistService  # noqa: E402

st.set_page_config(page_title="Fashion Assistant", layout="wide")
config.ensure_dirs()


@st.cache_resource
def get_svc():
    s = StylistService()
    trends.seed(s.c)
    return s


svc = get_svc()
c = svc.c
st.title("Fashion Assistant")
if not config.llm_enabled():
    st.info("No GEMINI_API_KEY: tagging, the AI critic and live trends are off. Rule-based looks, the demo wardrobe and learning still work.")

tab_style, tab_chat, tab_ward, tab_trend, tab_priv, tab_metrics = st.tabs(
    ["Style me", "Stylist chat (ADK)", "Wardrobe", "Trends", "Privacy and try-on", "Metrics"])


def show_plan(plan, key):
    cols = st.columns(len(plan["looks"]))
    w = plan["weather"]
    st.caption(f"{plan['session']['occasion']} | formality {plan['session']['formality']} | {w['temp_c']:.0f} C, {w['season']} ({w['source']})")
    for col, lk in zip(cols, plan["looks"]):
        with col:
            st.image(lk["collage_path"])
            st.markdown(f"**{lk['title']}**")
            st.write(lk["rationale"])
            with st.expander("Why this look"):
                st.json({"scores": lk["scores"], "rule_notes": lk["reasons"]})
            if st.button("Pick this look", key=f"{key}{lk['look_id']}", use_container_width=True):
                svc.choose(plan["session_id"], lk["look_id"])
                st.session_state.picked = lk["look_id"]
                st.toast("Saved. The stylist learned from this choice.")
    r1, r2 = st.columns([1, 2])
    reason = r1.selectbox("None of these because...", ["too formal", "too plain", "wrong colours", "other"], key=f"r{key}")
    if r2.button("None of these", key=f"n{key}"):
        svc.choose(plan["session_id"], None, reason)
        st.toast("Noted.")


with tab_style:
    a, b, d = st.columns(3)
    occ = a.selectbox("Occasion", config.OCCASIONS)
    form = b.slider("Formality (1 casual to 5 very formal)", 1, 5, config.OCCASION_FORMALITY.get(occ, 3))
    live = d.checkbox("Use live weather", True)
    avoid = st.multiselect("Colours to avoid", FAMILIES[1:])
    wear = st.multiselect("Colours I want to wear", FAMILIES[1:])
    if st.button("Style me", type="primary"):
        try:
            from fashion import context
            with st.spinner("Building looks..."):
                st.session_state.plan = svc.plan_looks(occ, form, avoid, wear, weather=None if live else {"temp_c": 27, "season": "all", "source": "manual"})
        except ValueError as e:
            st.error(str(e))
    if st.session_state.get("plan"):
        show_plan(st.session_state.plan, "s")
        picked = st.session_state.get("picked")
        if picked and st.button("Preview on me (optional)"):
            look = svc.get_look(picked)
            res = tryon.preview(c, look, tryon.PROVIDERS[st.session_state.get("provider", "hf_space")]())
            if res["mode"] == "tryon":
                db.log_metric(c, "tryon_qa", res["qa"]); db.log_metric(c, "tryon_s", res["seconds"])
            st.image(res["path"], caption=f"{res['mode']} | QA {res['qa']} | {res.get('reason', '')}")
            if res["mode"] == "collage":
                st.warning(res["reason"])

with tab_chat:
    if not stylist.available():
        st.info("Needs `pip install -r requirements-extra.txt` (google-adk) and a GEMINI_API_KEY. The form in 'Style me' does the same job.")
    else:
        if "agent" not in st.session_state:
            st.session_state.agent, st.session_state.sid, st.session_state.msgs = stylist.Stylist(svc), uuid.uuid4().hex, []
        for r, t in st.session_state.msgs:
            st.chat_message(r).write(t)
        if q := st.chat_input("e.g. my cousin's engagement, evening, indoor"):
            st.session_state.msgs.append(("user", q))
            before = svc.last_plan
            ans = st.session_state.agent.turn("owner", st.session_state.sid, q)
            st.session_state.msgs.append(("assistant", ans))
            st.rerun()
        if svc.last_plan:
            show_plan(svc.last_plan, "c")

with tab_ward:
    st.caption("Clothing and jewellery photos only. No face or body photos on the free tier. Photograph one earring or crop pairs to one.")
    l, r = st.columns(2)
    if l.button("Load 41-item demo wardrobe (no photos or API key needed)"):
        st.success(f"{demo.seed_demo(c)} demo items loaded"); st.rerun()
    up = r.file_uploader("Add item photos", accept_multiple_files=True, type=["jpg", "jpeg", "png", "webp"])
    if up and r.button("Tag uploads"):
        store = vectors.QdrantStore()
        for f in up:
            tmp = config.DATA_DIR / f"_upload_{f.name}"
            tmp.write_bytes(f.getbuffer())
            try:
                pipeline.ingest_image(tmp, store, c)
            except Exception as e:  # noqa: BLE001
                r.error(f"{f.name}: {e}")
            tmp.unlink(missing_ok=True)
    items = db.list_items(c)
    done = sum(i["tags_reviewed"] for i in items)
    st.progress(done / len(items) if items else 0.0, text=f"{done}/{len(items)} reviewed (goal: 60)")
    show = st.radio("Show", ["Unreviewed", "All"], horizontal=True)
    for it in items:
        if show == "Unreviewed" and it["tags_reviewed"]:
            continue
        t, k = it["tags"], it["item_id"]
        with st.expander(f"{k}: {t['kind']} / {t['subtype']}", expanded=not it["tags_reviewed"]):
            x, y = st.columns([1, 2])
            x.image(it["cutout_path"])
            kinds, pats = list(get_args(Kind)), list(get_args(Pattern))
            t["kind"] = y.selectbox("kind", kinds, kinds.index(t["kind"]), key=f"k{k}")
            t["subtype"] = y.text_input("subtype", t["subtype"], key=f"s{k}")
            t["primary_color_hex"] = y.color_picker("primary colour", t["primary_color_hex"], key=f"c{k}").upper()
            t["pattern"] = y.selectbox("pattern", pats, pats.index(t["pattern"]), key=f"p{k}")
            t["formality"] = y.slider("formality", 1, 5, t["formality"], key=f"f{k}")
            t["occasions"] = y.multiselect("occasions", sorted(set(config.OCCASIONS) | set(t["occasions"])), t["occasions"], key=f"o{k}")
            if y.button("Save and mark reviewed", key=f"b{k}"):
                db.update_tags(c, k, ItemTags(**t).model_dump()); st.rerun()

with tab_trend:
    st.caption("Paraphrased notes with links only. Never copied text or images. No Pinterest scraping.")
    if st.button("Refresh trends (Gemini + Google Search grounding)", disabled=not config.llm_enabled()):
        try:
            st.success(f"{trends.refresh(c)} notes added")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
    for n in sorted(trends.active_notes(c), key=lambda n: -n["weight"]):
        st.write(f"**{n['weight']:.2f}** {n['summary']}  `{', '.join(n['tags'])}`  [{n['source_name'] or 'source'}]({n['source_url']})" if n["source_url"]
                 else f"**{n['weight']:.2f}** {n['summary']}  `{', '.join(n['tags'])}`  ({n['source_name']})")

with tab_priv:
    ok, why = privacy.person_photos_allowed(c)
    st.write(f"Person photos allowed: **{ok}** ({why})")
    st.warning("Try-on needs a photo of you. On the free Gemini tier, content may be used to improve Google products, and a public Hugging Face Space is a third party. "
               "Use a stock model photo, or switch to a paid no-training setup, set ALLOW_PERSON_PHOTOS=true and consent below.")
    if st.checkbox("I consent to storing an encrypted copy of my photo", value=privacy.has_consent(c)) and not privacy.has_consent(c):
        privacy.record_consent(c); st.rerun()
    photo = st.file_uploader("Your photo", type=["jpg", "jpeg", "png"])
    if photo and st.button("Save encrypted"):
        try:
            privacy.save_user_photo(c, photo.getvalue()); st.success("Saved (encrypted).")
        except PermissionError as e:
            st.error(str(e))
    st.selectbox("Try-on provider", list(tryon.PROVIDERS), key="provider")
    st.divider()
    if st.button("Delete everything (photo, history, learned taste, wardrobe)", type="primary"):
        st.json(svc.delete_everything()); st.cache_resource.clear()

with tab_metrics:
    st.write("Run `python eval/report.py summary` for the full report. Live numbers:")
    n = c.execute("SELECT COUNT(*) FROM choice_event").fetchone()[0]
    st.metric("Choices logged", n); st.metric("Learner updates", svc.learner.n)
    rows = c.execute("SELECT name, ROUND(AVG(value),3) v, COUNT(*) n FROM metric GROUP BY name").fetchall()
    st.table([dict(r) for r in rows])
