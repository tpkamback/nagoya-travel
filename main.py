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
