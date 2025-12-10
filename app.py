from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from config import SessionLocal, engine, Base
from models import Revista, Artigo
from aws_config import upload_s3, log_dynamodb, S3_BUCKET, dynamodb, s3
import boto3
from datetime import datetime
from decimal import Decimal

# Criar tabelas (RDS)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Revistas e Artigos")

# Arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================================
# 📌 Função auxiliar: buscar logs
# ================================
def listar_logs():
    try:
        table = dynamodb.Table("Logs")
        response = table.scan(Limit=15)
        logs = response.get("Items", [])

        for log in logs:
            ts = log.get("timestamp", "")
            hora = "—"

            try:
                # Decimal (timestamp)
                if isinstance(ts, Decimal):
                    ts = int(ts)
                    hora = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

                # int ou float
                elif isinstance(ts, (int, float)):
                    hora = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")

                # string numérica
                elif isinstance(ts, str) and ts.isdigit():
                    hora = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")

                # string já formatada
                else:
                    hora = ts

            except Exception:
                hora = str(ts)

            log["hora"] = hora
            log["acao"] = log.get("acao", "—").upper()
            log["detalhes"] = log.get("detalhes", log.get("dados", "—"))

        # Ordenar mais recentes primeiro
        logs.sort(key=lambda x: x.get("hora", ""), reverse=True)

        print("Logs prontos:", logs[:3])
        return logs

    except Exception as e:
        print("⚠️ Erro ao buscar logs:", e)
        return []


# ================================
# 📌 Página principal
# ================================
@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    revistas = db.query(Revista).all()
    artigos = db.query(Artigo).all()
    logs = listar_logs()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "revistas": revistas, "artigos": artigos, "logs": logs},
    )


# ================================
# 📌 REVISTAS
# ================================
@app.post("/adicionar_revista")
def adicionar_revista(nome: str = Form(...), db: Session = Depends(get_db)):
    nova_revista = Revista(nome=nome)
    db.add(nova_revista)
    db.commit()

    log_dynamodb("CRIAR_REVISTA", nome)
    #publish_sns(f"Nova revista criada: {nome}", "Revista Criada")

    return RedirectResponse("/", status_code=303)


@app.post("/editar_revista/{revista_id}")
def editar_revista(revista_id: int, nome: str = Form(...), db: Session = Depends(get_db)):
    revista = db.query(Revista).filter(Revista.id == revista_id).first()
    if revista:
        revista.nome = nome
        db.commit()

        log_dynamodb("EDITAR_REVISTA", f"Revista {revista_id} atualizada para {nome}")
        #publish_sns(f"Revista {revista_id} atualizada", "Edição de Revista")

    return RedirectResponse("/", status_code=303)


@app.get("/excluir_revista/{revista_id}")
def excluir_revista(revista_id: int, db: Session = Depends(get_db)):
    revista = db.query(Revista).filter(Revista.id == revista_id).first()

    if revista:
        # Registrar log antes de excluir
        log_dynamodb("EXCLUIR_REVISTA", f"Revista {revista_id} excluída")
        #publish_sns(f"Revista {revista_id} excluída", "Exclusão de Revista")

        db.delete(revista)
        db.commit()

    return RedirectResponse("/", status_code=303)


# ================================
# 📌 ARTIGOS
# ================================
@app.post("/adicionar_artigo")
def adicionar_artigo(
    titulo: str = Form(...),
    autor: str = Form(...),
    resumo: str = Form(...),
    revista_id: int = Form(...),
    arquivo: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    artigo = Artigo(
        titulo=titulo, autor=autor, resumo=resumo, revista_id=revista_id
    )
    db.add(artigo)
    db.commit()
    db.refresh(artigo)

    # Upload do arquivo para S3
    if arquivo:
        key = f"artigos/{artigo.id}/{arquivo.filename}"
        upload_s3(arquivo.file, key)

        log_dynamodb("UPLOAD_ARQUIVO", f"{arquivo.filename} -> {S3_BUCKET}/{key}")
        #publish_sns(
        #    f"Upload do arquivo {arquivo.filename} concluído.",
        #    "Upload Realizado"
        #)

    log_dynamodb("CRIAR_ARTIGO", titulo)
    #publish_sns(f"Novo artigo criado: {titulo}", "Artigo Criado")

    return RedirectResponse("/", status_code=303)


@app.post("/editar_artigo/{artigo_id}")
def editar_artigo(
    artigo_id: int,
    titulo: str = Form(...),
    autor: str = Form(...),
    resumo: str = Form(...),
    db: Session = Depends(get_db),
):
    artigo = db.query(Artigo).filter(Artigo.id == artigo_id).first()
    if artigo:
        artigo.titulo = titulo
        artigo.autor = autor
        artigo.resumo = resumo
        db.commit()

        log_dynamodb("EDITAR_ARTIGO", f"Artigo {artigo_id} atualizado")
        #publish_sns(f"Artigo {artigo_id} atualizado", "Edição de Artigo")

    return RedirectResponse("/", status_code=303)


# ================================
# 📌 EXCLUSÃO DE ARTIGO (MinIO)
# ================================
@app.get("/excluir_artigo/{artigo_id}")
def excluir_artigo(artigo_id: int, db: Session = Depends(get_db)):
    artigo = db.query(Artigo).filter(Artigo.id == artigo_id).first()

    if artigo:
        prefix = f"artigos/{artigo_id}/"

        try:
            # Usar o cliente S3 configurado para MinIO
            paginator = s3.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
                contents = page.get("Contents", [])
                if contents:
                    keys = [{"Key": obj["Key"]} for obj in contents]

                    # Excluir em lote
                    resp = s3.delete_objects(
                        Bucket=S3_BUCKET,
                        Delete={"Objects": keys}
                    )

                    for d in resp.get("Deleted", []):
                        print(f"🗑️ Arquivo apagado: {d.get('Key')}")

        except Exception as e:
            print(f"❌ Erro ao excluir arquivos do MinIO: {e}")

        # Registrar log
        log_dynamodb("EXCLUIR_ARTIGO", f"Artigo {artigo_id} excluído")

        # Remover do banco
        db.delete(artigo)
        db.commit()

    return RedirectResponse("/", status_code=303)



# ================================
# Execução local
# ================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
