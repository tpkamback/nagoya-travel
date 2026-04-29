from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import models
from database import engine, get_db
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="名古屋旅行2026")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def seed_initial_data():
    """DBが空のときだけ初期データを投入する"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(models.Day).count() > 0:
            return  # 既にデータあり

        # ===== 5/3 =====
        day1 = models.Day(
            date="2025-05-03",
            title="移動日〜名古屋到着",
            description="盛岡から名古屋へ。竜也・直人と合流！",
        )
        db.add(day1)
        db.flush()
        db.add_all([
            models.Spot(day_id=day1.id, name="盛岡駅 → 東京駅",   category="移動", time="10:51", notes="10:51 → 13:04（新幹線）", order_index=0),
            models.Spot(day_id=day1.id, name="竜也と合流・移動",   category="移動", time="13:04", notes="13:04 → 14:00",           order_index=1),
            models.Spot(day_id=day1.id, name="東京駅 → 名古屋駅", category="移動", time="14:00", notes="14:00 → 15:39（新幹線）", order_index=2),
            models.Spot(day_id=day1.id, name="お土産探し",         category="観光", time="15:39", notes="15:39 → 16:30",           order_index=3),
            models.Spot(day_id=day1.id, name="直人と合流・直人家", category="観光", time="16:30", notes="16:30 → 18:00（様子見て時間変更あり）", order_index=4),
            models.Spot(day_id=day1.id, name="夕飯",               category="食事", time="18:00", notes="18:00 → 19:00",           order_index=5),
            models.Spot(day_id=day1.id, name="ホテルに移動",       category="宿泊", time="19:00", notes="",                        order_index=6),
        ])

        # ===== 5/4 =====
        day2 = models.Day(
            date="2025-05-04",
            title="名古屋→東京〜帰路",
            description="竜也家に立ち寄り、上野でお土産を買って盛岡へ帰宅！",
        )
        db.add(day2)
        db.flush()
        db.add_all([
            models.Spot(day_id=day2.id, name="名古屋駅集合",       category="移動", time="9:50",  notes="名古屋駅に集合",          order_index=0),
            models.Spot(day_id=day2.id, name="名古屋駅 → 東京駅", category="移動", time="10:00", notes="10:00 → 11:39（新幹線）", order_index=1),
            models.Spot(day_id=day2.id, name="竜也家着",           category="観光", time="11:39", notes="11:39 → 12:42",           order_index=2),
            models.Spot(day_id=day2.id, name="触れ合い＋ご飯",    category="食事", time="12:42", notes="12:42 → 14:36",           order_index=3),
            models.Spot(day_id=day2.id, name="上野駅に移動",       category="移動", time="14:36", notes="14:36 → 15:21",           order_index=4),
            models.Spot(day_id=day2.id, name="お土産（上野）",     category="観光", time="15:21", notes="15:21 → 16:20",           order_index=5),
            models.Spot(day_id=day2.id, name="上野駅 → 盛岡駅",   category="移動", time="16:20", notes="16:20 → 18:33（新幹線）", order_index=6),
        ])

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"seed error: {e}")
    finally:
        db.close()


seed_initial_data()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SESSION_COOKIE = "nagoya_admin"

CATEGORIES = ["観光", "食事", "カフェ", "宿泊", "移動"]


def is_admin(request: Request) -> bool:
    return request.cookies.get(SESSION_COOKIE) == "ok"


# ===== 公開ページ =====

@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    days = db.query(models.Day).order_by(models.Day.date).all()
    return templates.TemplateResponse("index.html", {"request": request, "days": days})


@app.get("/day/{day_id}")
def day_detail(day_id: int, request: Request, db: Session = Depends(get_db)):
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="見つかりません")
    return templates.TemplateResponse("day.html", {"request": request, "day": day})


# ===== 管理者ログイン =====

@app.get("/admin/login")
def login_page(request: Request, error: Optional[str] = None):
    if is_admin(request):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": error})


@app.post("/admin/login")
def login(password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse("/admin", status_code=302)
        response.set_cookie(SESSION_COOKIE, "ok", httponly=True, samesite="strict")
        return response
    return RedirectResponse("/admin/login?error=1", status_code=302)


@app.get("/admin/logout")
def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ===== 管理者ダッシュボード =====

@app.get("/admin")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    days = db.query(models.Day).order_by(models.Day.date).all()
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "days": days})


# ===== 日程 CRUD =====

@app.get("/admin/days/new")
def new_day_form(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse("admin/day_form.html", {"request": request, "day": None})


@app.post("/admin/days")
def create_day(
    request: Request,
    date: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    db.add(models.Day(date=date, title=title, description=description))
    db.commit()
    return RedirectResponse("/admin", status_code=302)


@app.get("/admin/days/{day_id}/edit")
def edit_day_form(day_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/day_form.html", {"request": request, "day": day})


@app.post("/admin/days/{day_id}/edit")
def update_day(
    day_id: int,
    request: Request,
    date: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404)
    day.date, day.title, day.description = date, title, description
    db.commit()
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/days/{day_id}/delete")
def delete_day(day_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if day:
        db.delete(day)
        db.commit()
    return RedirectResponse("/admin", status_code=302)


# ===== スポット CRUD =====

@app.get("/admin/days/{day_id}/spots/new")
def new_spot_form(day_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "admin/spot_form.html",
        {"request": request, "day": day, "spot": None, "categories": CATEGORIES},
    )


@app.post("/admin/days/{day_id}/spots")
def create_spot(
    day_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    time: str = Form(""),
    notes: str = Form(""),
    map_url: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404)
    spot = models.Spot(
        day_id=day_id,
        name=name,
        category=category,
        time=time,
        notes=notes,
        map_url=map_url,
        order_index=len(day.spots),
    )
    db.add(spot)
    db.commit()
    return RedirectResponse(f"/admin/days/{day_id}/spots", status_code=302)


@app.get("/admin/days/{day_id}/spots")
def list_spots(day_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    day = db.query(models.Day).filter(models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/spots.html", {"request": request, "day": day})


@app.get("/admin/spots/{spot_id}/edit")
def edit_spot_form(spot_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    spot = db.query(models.Spot).filter(models.Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "admin/spot_form.html",
        {"request": request, "day": spot.day, "spot": spot, "categories": CATEGORIES},
    )


@app.post("/admin/spots/{spot_id}/edit")
def update_spot(
    spot_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    time: str = Form(""),
    notes: str = Form(""),
    map_url: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    spot = db.query(models.Spot).filter(models.Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404)
    spot.name, spot.category, spot.time = name, category, time
    spot.notes, spot.map_url = notes, map_url
    db.commit()
    return RedirectResponse(f"/admin/days/{spot.day_id}/spots", status_code=302)


@app.post("/admin/spots/{spot_id}/delete")
def delete_spot(spot_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    spot = db.query(models.Spot).filter(models.Spot.id == spot_id).first()
    if spot:
        day_id = spot.day_id
        db.delete(spot)
        db.commit()
        return RedirectResponse(f"/admin/days/{day_id}/spots", status_code=302)
    return RedirectResponse("/admin", status_code=302)
