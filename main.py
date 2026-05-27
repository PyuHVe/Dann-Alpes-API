from datetime import datetime
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson.objectid import ObjectId

app = FastAPI()

# Configuración de CORS para permitir peticiones desde cualquier cliente
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==========================================
# Configuración de Base de Datos
# ==========================================

client = MongoClient(os.environ["MONGO_URI"])
db = client["ISIS2304J18202610"]

# =================================================
# Endpoints de requerimientos funcionales
# =================================================

@app.get("/")
def inicio():
    """Endpoint de verificación de estado."""
    return {"estado": "API funcionando correctamente"}

@app.get("/reviews/hotel/{hotel_id}")
def get_reviews_hotel(hotel_id: int) -> list|dict:
    result = {}
    reviews = list(db["resenas"].find({"hotel_id":hotel_id}))
    if len(reviews) > 0:
        for review in reviews:
            review["_id"] = str(review["_id"])
        result = reviews
    return result

@app.get("/reviews/client/{cliente_id}")
def get_reviews_client(cliente_id: int) -> list|dict:
    result = {}
    reviews = list(db["resenas"].find({"cliente_id":cliente_id}))
    if len(reviews) > 0:
        for review in reviews:
            review["_id"] = str(review["_id"])
        result = reviews
    return result

@app.post("/reviews/{hotel_id}")
def post_review(hotel_id: int, data: dict) -> dict:
    data['hotel_id'] = hotel_id
    data["fecha_creacion"] = datetime.now()
    db["resenas"].insert_one(data)
    return {'mensaje': "Reseña enviada correctamente"}

@app.patch("/reviews/client/{review_id}")
def update_review(review_id: str, data: dict) -> dict:
    db["resenas"].update_one({"_id":ObjectId(review_id)}, {"$set":data})
    return {"mensaje":"Reseña actualizada correctamente"}

@app.patch("/reviews/votes/{review_id}")
def update_vote_count(review_id: str) -> None:
    db["resenas"].update_one({"_id":ObjectId(review_id)}, {"$inc":{"votos_count":1}})

@app.patch("/reviews/admin/answer/{admin_id}/{review_id}")
def respond_review(admin_id: int, review_id: str, data: dict) -> dict:
    data["respuesta"]["admin_id"] = admin_id
    data["respuesta"]["fecha"] = datetime.now()
    db["resenas"].update_one({"_id":ObjectId(review_id)}, {"$set":data})
    return {"mensaje": "Respuesta agregada correctamente"}

@app.patch("/reviews/admin/highlight/{review_id}")
def highlight_review(review_id: str) -> None:
    highlight = db["resenas"].find_one({"_id":ObjectId(review_id)},{"destacada":1})["destacada"]
    db["resenas"].update_one({"_id":ObjectId(review_id)}, {"$set":{"destacada":not(highlight)}})

@app.delete("/reviews/{review_id}")
def delete_review(review_id: str) -> dict:
    db["resenas"].delete_one({"_id":ObjectId(review_id)})
    return {"mensaje": "Reseña eliminada correctamente"}

# ===========================================================
# Endpoints de requerimientos funcionales de consulta
# ===========================================================

@app.get("/reviews/query/top10/{start_date}/{end_date}")
def get_top_hotels(start_date: str, end_date: str) -> list|dict:
    result = {}
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    top_10 = list(db["resenas"].aggregate([
        {'$addFields': {'fecha_dt': {'$dateFromString': {'dateString': '$fecha_creacion'}}}},
        {'$match': {'fecha_dt': {'$gte': start_dt, '$lte': end_dt}}},
        {'$group': {'_id': '$hotel_id', 'promedio_calificaciones': {'$avg': '$calificacion'}, 'total_resenas': {'$sum': 1}}},
        {'$sort': {'promedio_calificaciones': -1}},
        {'$limit': 10}
    ]))
    if len(top_10) > 0:
        result = top_10
    return result

@app.get("/reviews/query/hotel_reputation/{hotel_id}/{year}")
def get_hotel_reputation(hotel_id: int, year: int) -> list|dict:
    result = {}
    hotel_reputation = list(db["resenas"].aggregate([{'$set':{'mes':{'$month':'$fecha_creacion'}, 'anio':{'$year':'$fecha_creacion'}}}, {'$match':{'anio':year, 'hotel_id':hotel_id}},
    {"$project":{"_id":0}}, {'$group': {'_id': '$mes', 'promedio_calificaciones': {'$avg': '$calificacion'}}}]))
    if len(hotel_reputation) > 0:
        result = hotel_reputation
    return result

@app.get("/reviews/query/hotels_profiles/{hotel_id}")
def get_hotels_profiles(hotel_id: int) -> list|dict:
    result = {}
    hotels_profiles = list(db["resenas"].aggregate([{'$match':{'hotel_id':hotel_id}}, {'$group':{'_id':None, 'promedio_calificaciones':{'$avg':'$calificacion'}, 'total_resenas':{'$sum':
    1}, "resp_admin":{"$sum":{"$cond":[{'$ne':['$respuesta', None]}, 1, 0]}}, "destacadas":{"$sum":{"$cond":["$destacada", 1, 0]}}}},
    {'$project':{'_id':0, 'hotel_id':1, 'promedio_calificaciones':1, 'total_resenas':1, 'porcentaje_resp_admin':{'$multiply':[{'$divide':['$resp_admin', '$total_resenas']}, 100]},
    'porcentaje_destacadas':{'$multiply':[{'$divide':['$destacadas', '$total_resenas']}, 100]}}}]))
    if len(hotels_profiles) > 0:
        result = hotels_profiles
    return result
