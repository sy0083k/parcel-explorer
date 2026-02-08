# app/routers/auth.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # main.py에서 등록한 공통 템플릿 엔진 사용
    templates = request.app.state.templates
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    templates = request.app.state.templates
    
    # 예시 로그인 로직 (실제 프로젝트에 맞게 수정하세요)
    if username == "admin" and password == "1234":
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value="authenticated")
        return response
        
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "아이디 또는 비밀번호가 틀렸습니다."
    })

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    return response