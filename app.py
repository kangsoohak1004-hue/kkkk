"""게으름 탈출구 | 실행: streamlit run app.py
GitHub에는 app.py와 requirements.txt만 업로드하세요.
Supabase SQL과 Streamlit Secrets 예시는 앱의 관리자 설정 안내에 있습니다.
한 가족 전용 배포입니다. 가족 코드는 기록 공유용이며 비밀번호를 대신하지 않습니다.
"""
import base64
import calendar
import copy
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

st.set_page_config(page_title="게으름 탈출구", page_icon="🌱", layout="wide")
TODAY = datetime.now(ZoneInfo("Asia/Seoul")).date()
DAYS = ["월", "화", "수", "목", "금", "토", "일"]
SQL = '''create table if not exists public.family_planner (
  id text primary key,
  state jsonb not null default '{}'::jsonb,
  version bigint not null default 0
);
alter table public.family_planner enable row level security;
revoke all on public.family_planner from anon, authenticated;
-- 공개 접근 정책은 만들지 않습니다. 서버 전용 service_role 키로 연결합니다.
'''
SECRET_EXAMPLE = '''SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "서버 전용 service_role 키"
CHILD_PASSWORD = "자녀용-긴-비밀번호"
PARENT_PASSWORD = "부모님만-아는-다른-긴-비밀번호"
'''
st.markdown("""<style>
.stApp {background: #F7FAF8;}
[data-testid="stMetric"] {background:white; padding:16px; border-radius:16px; border:1px solid #DBE8DF;}
[data-testid="stSidebar"] {background:#EDF5EF;}
</style>""", unsafe_allow_html=True)


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def signout():
    st.session_state.clear()
    st.rerun()


def setup_guide():
    with st.expander("⚙️ 관리자 설정 안내", expanded=False):
        st.write("가족 기록과 사진을 공유하려면 Supabase 저장소를 연결하세요. 소개 화면은 설정 없이 볼 수 있습니다.")
        st.markdown("1. Supabase에서 프로젝트를 만듭니다.\n2. SQL Editor에서 아래 SQL을 실행합니다.\n3. Streamlit 앱 설정 → Secrets에 연결 정보와 서로 다른 부모님·자녀 비밀번호를 입력합니다.")
        st.code(SQL, language="sql")
        st.code(SECRET_EXAMPLE, language="toml")
        st.warning("서버 키와 비밀번호를 GitHub에 올리지 마세요. 한 가족마다 별도 앱 배포를 권장합니다. 코드는 가족끼리만 공유하세요.")
        st.caption("기존 family_planner 테이블을 이미 만들었다면 그대로 사용할 수 있습니다. 이전 버전 기록은 자동 이전되지 않으며, 새 가족 코드를 만들면 새 기록으로 시작합니다.")


if "entered" not in st.session_state:
    st.title("🌱 게으름 탈출구")
    st.subheader("오늘의 작은 실천을, 반짝이는 코인으로!")
    st.write("부모님과 함께 주간 계획을 세우고, 숙제를 마친 사진을 올리는 생활 습관 앱이에요. 부모님이 확인하고 승인하면 코인이 차곡차곡 쌓여요.")
    a, b, c = st.columns(3)
    a.info("🔗 가족 코드\n\n코드를 만들어 부모님과 같은 공간에 들어가요.")
    b.info("📅 계획과 인증\n\n요일별 계획을 세우고 카메라로 인증해요.")
    c.info("🪙 승인과 코인\n\n부모님이 승인하면 약속한 코인을 받아요.")
    if st.button("우리 가족 시작하기 →", type="primary", use_container_width=True):
        st.session_state.entered = True
        st.rerun()
    st.caption("코인은 앱 안의 보상 점수입니다. 현금·용돈으로 자동 환전하거나 송금하지 않습니다.")
    setup_guide()
    st.stop()

required = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "CHILD_PASSWORD", "PARENT_PASSWORD"]
try:
    configured = all(str(st.secrets.get(k, "")).strip() for k in required)
except Exception:
    configured = False
if not configured:
    st.title("🔗 우리 가족 공간 준비하기")
    st.info("앱 소개는 준비됐어요! 가족 코드와 인증 기능을 사용하려면 관리자 설정을 먼저 완료해주세요.")
    setup_guide()
    if st.button("← 앱 소개로"):
        signout()
    st.stop()
if str(st.secrets["CHILD_PASSWORD"]) == str(st.secrets["PARENT_PASSWORD"]):
    st.error("Secrets에서 부모님과 자녀 비밀번호를 서로 다르게 설정해주세요.")
    st.stop()

if "role" not in st.session_state:
    st.title("🔐 누가 들어왔나요?")
    st.caption("가족 코드를 만들거나 입력하기 전에 본인의 역할로 로그인하세요.")
    with st.form("login"):
        role = st.radio("사용자", ["자녀", "부모님"], horizontal=True)
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("다음 →", type="primary", use_container_width=True)
    if submit:
        key = "PARENT_PASSWORD" if role == "부모님" else "CHILD_PASSWORD"
        if hmac.compare_digest(digest(password), digest(st.secrets[key])):
            st.session_state.role = role
            st.session_state.auth = digest(st.secrets[key])
            st.rerun()
        else:
            st.error("비밀번호를 확인해주세요.")
    st.caption("부모님 비밀번호는 자녀에게 알려주지 마세요. 공용 기기에서는 로그아웃하세요.")
    st.stop()

parent = st.session_state.role == "부모님"
key = "PARENT_PASSWORD" if parent else "CHILD_PASSWORD"
if not hmac.compare_digest(st.session_state.get("auth", ""), digest(st.secrets[key])):
    signout()
try:
    db = create_client(str(st.secrets["SUPABASE_URL"]), str(st.secrets["SUPABASE_SERVICE_ROLE_KEY"]))
except Exception:
    st.error("저장소 연결 설정을 확인해주세요.")
    st.stop()


def family_key(code):
    return "pair_" + digest(code)


def load_family(code):
    return db.table("family_planner").select("state,version").eq("id", family_key(code)).execute().data


if "family_code" not in st.session_state:
    st.title("🔗 가족 코드로 함께하기")
    st.write("처음이라면 코드를 만들고, 부모님 또는 자녀에게 코드를 알려주세요. 이미 코드가 있다면 입력하세요.")
    create_tab, join_tab = st.tabs(["✨ 코드 생성", "🔑 코드 입력"])
    with create_tab:
        st.info("생성한 코드는 따로 적어두세요. 다른 기기에서 같은 코드를 입력하면 가족 달력이 열립니다.")
        if st.button("새 가족 코드 만들기", type="primary", use_container_width=True):
            try:
                code = secrets.token_hex(5).upper()
                initial = {"schema": 2, "tasks": [], "created": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}
                db.table("family_planner").insert({"id": family_key(code), "state": initial, "version": 0}).execute()
                st.session_state.family_code = code
                st.rerun()
            except Exception:
                st.error("코드를 만들지 못했습니다. Supabase SQL·연결 설정을 확인한 뒤 다시 시도해주세요.")
    with join_tab:
        with st.form("join"):
            code = st.text_input("부모님 또는 자녀에게 받은 가족 코드", max_chars=20, placeholder="예: 12AB34CD56").strip().upper()
            join = st.form_submit_button("가족 달력 열기 →", use_container_width=True)
        if join:
            if len(code) != 10 or any(ch not in "0123456789ABCDEF" for ch in code):
                st.warning("10자리 영문·숫자 코드를 확인해주세요.")
            else:
                try:
                    rows = load_family(code)
                    if rows and rows[0]["state"].get("schema") == 2:
                        st.session_state.family_code = code
                        st.rerun()
                    else:
                        st.error("해당 가족 코드를 찾지 못했어요. 코드를 다시 확인해주세요.")
                except Exception:
                    st.error("코드를 확인하지 못했습니다. 저장소 연결을 확인해주세요.")
    if st.button("로그아웃"):
        signout()
    st.stop()

code = st.session_state.family_code
try:
    rows = load_family(code)
    if not rows:
        st.error("가족 기록이 없습니다. 다른 코드로 다시 입장해주세요.")
        if st.button("코드 다시 입력"):
            del st.session_state.family_code
            st.rerun()
        st.stop()
    original = rows[0]
    state = copy.deepcopy(original["state"])
    if state.get("schema") != 2:
        st.error("이 버전과 다른 형식의 가족 기록입니다. 새 가족 코드로 시작해주세요.")
        st.stop()
    tasks = state.setdefault("tasks", [])
except Exception:
    st.error("가족 기록을 읽지 못했습니다. 연결 설정을 확인하고 새로고침해주세요.")
    st.stop()


def save(message):
    if len(json.dumps(state).encode()) > 18_000_000:
        st.error("가족 데이터 용량이 가득 찼습니다. 부모님이 승인 완료된 사진을 정리해주세요.")
        st.stop()
    try:
        changed = db.table("family_planner").update({"state": state, "version": original["version"] + 1}).eq("id", family_key(code)).eq("version", original["version"]).execute().data
    except Exception:
        st.error("저장하지 못했습니다. 잠시 후 다시 시도해주세요.")
        st.stop()
    if not changed:
        st.warning("다른 가족이 먼저 수정했어요. ‘최신 기록 새로고침’을 누른 뒤 다시 시도해주세요. 이번 변경은 저장되지 않았습니다.")
        st.stop()
    st.session_state.notice = message
    st.rerun()


def coin_total(items):
    return sum(int(t["coins"]) for t in items if t["status"] == "approved")


st.sidebar.title("🌱 게으름 탈출구")
st.sidebar.write(f"**{st.session_state.role} 공간**")
st.sidebar.markdown("#### 우리 가족 코드")
st.sidebar.code(code, language=None)
st.sidebar.caption("이 코드를 가족에게 알려주세요. 로그인 비밀번호도 별도로 필요합니다.")
if st.sidebar.button("🔄 최신 기록 새로고침", use_container_width=True):
    st.rerun()
if st.sidebar.button("다른 가족 코드 입력", use_container_width=True):
    del st.session_state.family_code
    st.rerun()
if st.sidebar.button("로그아웃", use_container_width=True):
    signout()
with st.sidebar.expander("사용 규칙과 개인정보"):
    st.write("자녀가 계획을 올리면 부모님이 보상 코인과 계획을 확정합니다. 자녀가 인증을 제출하고 부모님이 승인하면 코인이 쌓입니다. 승인된 과제는 다시 적립되지 않습니다.")
    st.write("사진은 가족 저장소에 보관됩니다. 얼굴·이름·학교·주소가 드러나지 않게 찍어주세요. 카메라 권한을 허용해야 촬영할 수 있으며, 사진 업로드로 대신할 수 있습니다.")
    st.caption("사진 한 장당 최대 1MB, 가족 전체 데이터 약 18MB 제한. 사진을 지워도 승인과 코인 기록은 유지됩니다. 다른 사람의 새 기록은 자동 반영되지 않으므로 새로고침하세요.")

if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))
st.title("📅 우리 가족 실천 달력")
a, b, c = st.columns(3)
a.metric("🪙 모은 코인", f"{coin_total(tasks):,}")
b.metric("승인 완료", f"{sum(t['status'] == 'approved' for t in tasks)}개")
c.metric("부모님 확인 대기", f"{sum(t['status'] == 'pending' for t in tasks)}개")

cal_tab, review_tab, coins_tab = st.tabs(["📅 달력과 숙제 인증", "✅ 부모님 승인", "🪙 코인 기록"])
with cal_tab:
    if "month" not in st.session_state:
        st.session_state.month = TODAY.replace(day=1)
    month = st.session_state.month
    left, middle, right = st.columns([1, 3, 1])
    with left:
        if st.button("← 이전 달", use_container_width=True):
            st.session_state.month = (month - timedelta(days=1)).replace(day=1)
            st.rerun()
    middle.subheader(f"{month.year}년 {month.month}월")
    with right:
        if st.button("다음 달 →", use_container_width=True):
            st.session_state.month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
            st.rerun()
    st.caption("요일 아래 날짜를 누르면 그날의 계획과 인증 카메라가 나타나요. · 숫자 뒤 괄호는 등록한 계획 수예요.")
    for col, dayname in zip(st.columns(7), DAYS):
        col.markdown(f"**{dayname}**")
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month):
        cols = st.columns(7)
        for col, day in zip(cols, week):
            count = sum(t["day"] == day.isoformat() for t in tasks)
            label = f"{'● ' if day == TODAY else ''}{day.day}" + (f" ({count})" if count else "")
            with col:
                if st.button(label, key=f"day_{day}", disabled=day.month != month.month, use_container_width=True):
                    st.session_state.selected_day = day
                    st.rerun()
    selected = st.session_state.get("selected_day", TODAY)
    st.divider()
    st.subheader(f"{selected:%Y년 %m월 %d일} ({DAYS[selected.weekday()]})")
    selected = st.date_input("계획하거나 인증할 날짜", value=selected, key=f"pick_{selected.isoformat()}")
    st.caption("한 주의 여러 요일을 차례로 선택해 주간 계획을 세워보세요.")
    with st.expander("✏️ 이 날짜에 할 일 올리기", expanded=not any(t["day"] == selected.isoformat() for t in tasks)):
        with st.form(f"task_form_{selected}", clear_on_submit=True):
            title = st.text_input("할 일", max_chars=80, placeholder="예: 수학 숙제 3쪽 풀기")
            criterion = st.text_input("완료 기준", max_chars=200, placeholder="예: 풀이가 보이는 사진 찍기")
            submit_plan = st.form_submit_button("계획 올리기", type="primary")
        if submit_plan:
            if not title.strip() or not criterion.strip():
                st.warning("할 일과 완료 기준을 입력해주세요.")
            elif len(tasks) >= 300:
                st.warning("가족 계획은 최대 300개까지 등록할 수 있습니다.")
            else:
                tasks.append({"id": uuid.uuid4().hex, "title": title.strip(), "criterion": criterion.strip(), "day": selected.isoformat(), "coins": 10, "locked": False, "status": "todo", "evidence": None, "note": "", "feedback": ""})
                save("계획을 올렸어요! 부모님이 계획과 보상을 확정하면 인증할 수 있어요.")
    daily = [t for t in tasks if t["day"] == selected.isoformat()]
    if not daily:
        st.info("아직 계획이 없어요. 이 날짜에 할 일을 올려보세요!")
    status_names = {"todo": "실천 전", "pending": "부모님 확인 중", "retry": "다시 도전", "approved": "승인 완료"}
    for task in daily:
        tid = task["id"]
        with st.container(border=True):
            st.markdown(f"#### {task['title']}")
            st.write(f"완료 기준: {task['criterion']}")
            st.caption(f"{status_names[task['status']]} · 보상 {task['coins']}코인 · {'계획 확정' if task['locked'] else '부모님 계획 확정 대기'}")
            if task.get("feedback"):
                st.info(f"부모님 피드백: {task['feedback']}")
            if parent and not task["locked"]:
                reward = st.number_input("승인 시 받을 코인", min_value=1, max_value=10000, value=int(task["coins"]), key=f"reward_{tid}")
                if st.button("계획과 보상 확정", key=f"lock_{tid}"):
                    task["coins"] = int(reward)
                    task["locked"] = True
                    save("계획과 보상을 확정했어요.")
            if not task["locked"] and st.button("이 계획 삭제", key=f"delete_{tid}"):
                state["tasks"] = [t for t in tasks if t["id"] != tid]
                save("계획을 삭제했어요.")
            if task["status"] == "approved":
                st.success(f"부모님 승인 완료! {task['coins']}코인이 쌓였어요. 🪙")
            elif not parent and task["locked"] and task["status"] in ["todo", "retry"]:
                source = st.radio("인증 방법", ["📷 카메라 촬영", "🖼️ 사진 선택"], horizontal=True, key=f"source_{tid}")
                if source == "📷 카메라 촬영":
                    image = st.camera_input("숙제 인증 카메라", key=f"camera_{tid}_{task['status']}")
                else:
                    image = st.file_uploader("숙제 사진 선택", type=["jpg", "jpeg", "png"], key=f"upload_{tid}_{task['status']}")
                st.markdown("### 숙제를 올려보세요!")
                st.caption("촬영 전 브라우저의 카메라 사용을 허용해주세요. 카메라가 없다면 사진 선택을 이용하세요.")
                note = st.text_input("오늘의 실천 한마디 (선택)", max_chars=300, key=f"note_{tid}")
                if st.button("부모님께 인증 보내기", key=f"send_{tid}", type="primary"):
                    if image is None:
                        st.warning("사진을 먼저 촬영하거나 선택해주세요.")
                    elif image.size > 1_000_000:
                        st.warning("사진은 1MB 이하로 줄여주세요. 휴대폰 사진 크기를 낮춰 촬영할 수 있어요.")
                    else:
                        # Decode the image before saving so non-image content is rejected.
                        from io import BytesIO
                        from PIL import Image
                        try:
                            raw = image.getvalue()
                            with Image.open(BytesIO(raw)) as check:
                                check.verify()
                            task["evidence"] = base64.b64encode(raw).decode()
                            task["note"] = note.strip()
                            task["status"] = "pending"
                            save("부모님께 인증을 보냈어요! 승인되면 코인이 쌓여요.")
                        except (OSError, ValueError, Image.DecompressionBombError):
                            st.error("읽을 수 없는 사진입니다. JPG 또는 PNG 사진을 다시 선택해주세요.")
            elif not parent and task["status"] == "pending":
                st.info("부모님이 확인 중이에요. 승인되면 코인이 자동으로 반영돼요.")
            elif parent and task["locked"] and task["status"] == "todo":
                st.caption("자녀가 인증을 제출하면 ‘부모님 승인’ 탭에서 확인할 수 있어요.")

with review_tab:
    if not parent:
        st.info("인증 승인과 코인 지급은 부모님으로 로그인해야 할 수 있어요.")
    else:
        pending = [t for t in tasks if t["status"] == "pending"]
        st.subheader(f"확인할 숙제 {len(pending)}개")
        if not pending:
            st.success("지금은 확인할 숙제가 없어요.")
        for task in pending:
            tid = task["id"]
            with st.container(border=True):
                st.subheader(task["title"])
                st.write(f"{task['day']} · 완료 기준: {task['criterion']}")
                if task.get("evidence"):
                    st.image(base64.b64decode(task["evidence"]), caption="자녀가 제출한 인증 사진", width=450)
                st.write(task.get("note") or "인증 메모 없음")
                feedback = st.text_input("응원 또는 재도전 피드백", max_chars=300, key=f"feedback_{tid}")
                yes, no = st.columns(2)
                if yes.button(f"✅ 승인하고 {task['coins']}코인 쌓기", key=f"approve_{tid}", type="primary", use_container_width=True):
                    task["status"] = "approved"
                    task["feedback"] = feedback.strip()
                    task["approved_at"] = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
                    save(f"승인 완료! {task['coins']}코인이 적립됐어요.")
                if no.button("↩️ 다시 도전하기", key=f"retry_{tid}", use_container_width=True):
                    if not feedback.strip():
                        st.warning("어떤 부분을 보완하면 좋을지 알려주세요.")
                    else:
                        task["status"] = "retry"
                        task["feedback"] = feedback.strip()
                        task["evidence"] = None
                        save("재도전 피드백을 보냈어요.")
        with st.expander("저장 공간 관리: 승인된 사진 지우기"):
            st.caption("인증 사진만 지우며 계획·승인·적립 코인은 유지됩니다. 삭제한 사진은 복구할 수 없습니다.")
            agree = st.checkbox("승인된 사진을 모두 영구 삭제하는 데 동의합니다.")
            if st.button("승인된 사진만 삭제", disabled=not agree):
                for task in tasks:
                    if task["status"] == "approved":
                        task["evidence"] = None
                save("승인된 사진을 정리했어요. 코인과 승인 기록은 유지돼요.")

with coins_tab:
    st.subheader("🪙 나의 실천이 쌓인 코인")
    st.metric("누적 적립 코인", f"{coin_total(tasks):,}")
    st.caption("부모님이 승인한 숙제만 적립돼요. 같은 숙제는 한 번만 적립됩니다. 현재 코인은 소비·현금 전환 없는 누적 보상 점수입니다.")
    approved = sorted([t for t in tasks if t["status"] == "approved"], key=lambda t: t.get("approved_at", ""), reverse=True)
    if not approved:
        st.info("첫 인증 승인을 받고 첫 코인을 모아보세요!")
    for task in approved:
        with st.container(border=True):
            st.write(f"🪙 +{task['coins']} · {task['title']}")
            st.caption(f"계획 날짜 {task['day']} · 승인 {task.get('approved_at', '')[:10]}")

streamlit>=1.40,<2.0
supabase>=2.10,<3.0
Pillow>=10.0,<13.0
