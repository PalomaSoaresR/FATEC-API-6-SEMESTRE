from fastapi import APIRouter, Depends, HTTPException
import os
from pymongo import MongoClient
from ..core.calculo_tam import calculo_tam

# 4d6eefb1-a550-4371-b059-17b1157a6375
# 802e323f-3a26-4473-bb78-ba843a5dab88

router = APIRouter()

def get_db():
    user = os.getenv("MONGO_ROOT_USER", "root")
    pw = os.getenv("MONGO_ROOT_PASSWORD", "1234")
    host = os.getenv("MONGO_HOST", "mongodb")
    db_name = os.getenv("MONGO_DB", "fatec_api")
    
    uri = f"mongodb://{user}:{pw}@{host}:27017/?authSource=admin"
    
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[db_name]

@router.get('/tam/{job_id}')
async def get_json_tam(job_id: str, db=Depends(get_db)):

    try:

        calculo_trechos, ranking_conjunto, top_10_conjunto = calculo_tam(db, job_id) 

        return {
            "status": "success",
            "metadata": {
                "job_id": job_id,
            },
            "data": {
                "trechos": calculo_trechos,
                "ranking_por_conjunto": ranking_conjunto,
                "top_10": top_10_conjunto
            }
        }
    
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Erro interno ao processar TAM: {str(e)}')
