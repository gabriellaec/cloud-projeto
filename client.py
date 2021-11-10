from typing import Optional
from fastapi import FastAPI, status, Form, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from starlette.responses import RedirectResponse
import uvicorn


tags_metadata = [
    {
        "name": "disciplina",
        "description": "disciplinas que está cursando. Incluem nome, nome do professor, anotações e notas",
    }
]

description = """
    Microsserviço de controle de notas para um App para gerenciar disciplinas 🚀
    Permite:
       - Criar disciplinas e notas
       - Consultar informações de cada disciplina
       - Alterar disciplinas e notas
       - Deletar disciplinas e notas
"""


app = FastAPI(
    title="Minhas Disciplinas",
    description=description,
    version="0.0.1",
    openapi_tags=tags_metadata,
)


disciplinas = [
    {"id": 0, "name": "Megadados", "prof_name": "Ayres", "notes":"Projeto 1"},
    {"id": 1,"name": "cloud", "notes":"Roteiros"},
    {"id": 2,"name": "descomp", "prof_name": "Paulo", "notes":"?"}
]

id_num=len(disciplinas)



#---------------------------------------------------#
#    	             Disciplinas    	            #
#---------------------------------------------------#
#####################################################
# • O usuário pode criar uma disciplina
#####################################################
@app.post("/criar-disciplina/",  
status_code=status.HTTP_201_CREATED,
summary="Adicionar disciplina",
response_description="Adicionando disciplina",
tags=["disciplina"]
)
async def add(nome: str = Form(...), nome_prof: Optional[str] = Form(None), anotacoes: str = Form(...)):
    """
    Cria uma disciplina com todos os atributos
    - **nome**: A disciplina tem um nome único (obrigatório) - 
    - **nome do professor**: A disciplina tem um nome de professor (opcional)
    - **anotacoes**: A disciplina tem um campo de anotação livre (texto)
    """

# Garantindo que o nome da disciplina é único
    for i in range(len(disciplinas)):
        if disciplinas[i]["name"] == nome:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Disciplina já existe")
    
    
    global id_num
    new_disciplina = {
                      "id": id_num,
                      "name": nome, 
                      "prof_name": nome_prof, 
                      "notes": anotacoes,
                      } 
      
    id_num+=1 
    disciplinas.append(new_disciplina)
    result = disciplinas
    return {"nomes_disciplinas": [d for d in disciplinas]}



######################################################
# • O usuário pode listar os nomes de suas disciplinas
######################################################
@app.get("/nomes-disciplinas/",
status_code=status.HTTP_200_OK,
summary="Listar os nomes das disciplinas",
response_description="Listando as disciplinas",
tags=["disciplina"]
)
async def show():
    """
     Lê todas os nomes das disciplinas existentes
    """
    print(disciplinas)
    return {"nomes_disciplinas": [d["name"] for d in disciplinas]}




##################################################################################
#U • O usuário pode modificar as informações de uma disciplina INCLUINDO seu nome
##################################################################################
@app.put("/update-disciplina/", 
status_code=status.HTTP_200_OK,
summary="Atualizar disciplina",
response_description="Atualizando disciplina",
tags=["disciplina"]
)
async def update(nome_disciplina: str = Form(...), novo_nome_disciplina: Optional[str] = Form(None), nome_prof: Optional[str] = Form(None), anotacoes: Optional[str] = Form(None)):
    """
    Atualiza as informações de uma determinada disciplina
    - **nome_disciplina**: A disciplina que será alterada
    - **novo_nome_disciplina**: Novo nome que a disciplina receberá
    - **nome_prof**: Nome do professor que se deseja alterar
    - **anotacoes**: Novas anotacoes a serem alteradas
    """
  
# Checa se disciplina existe
    if not any(d["name"]==nome_disciplina for d in disciplinas):
            raise HTTPException(status_code=404, detail="Disciplina não encontrada")

# Pega a posição da lista em que a matéria está
    for i in range(len(disciplinas)):
        if disciplinas[i]["name"] == nome_disciplina:
            item_id=i

    nome_prof_old = disciplinas[item_id]["prof_name"]
    anotacoes_old = disciplinas[item_id]["notes"]
    grades = disciplinas[item_id]["grades"]
    id_disciplina = disciplinas[item_id]["id"]




    if nome_prof is None:
        nome_prof=nome_prof_old
    if anotacoes is None:
        anotacoes=anotacoes_old
    if novo_nome_disciplina is not None:
        nome_disciplina = novo_nome_disciplina
    
    new_disciplina = {
                      "id": id_disciplina,
                      "name": nome_disciplina, 
                      "prof_name": nome_prof, 
                      "notes": anotacoes,
                      } 
      
    disciplinas[item_id]=new_disciplina
    return disciplinas


##############################################
### • O usuário pode deletar uma disciplina
##############################################
@app.delete("/delete-disciplina/",
status_code=status.HTTP_200_OK,
summary="Deletar disciplina",
response_description="Deletando disciplina",
tags=["disciplina"]
)
def delete_disciplina(nome_disciplina: str = Form(...)):

# Checa se disciplina existe
    if not any(d["name"]==nome_disciplina for d in disciplinas):
            raise HTTPException(status_code=404, detail="Disciplina não encontrada")

# Se ela existe, encontra sua posição na lista
    for i in range(len(disciplinas)):
        if disciplinas[i]["name"] == nome_disciplina:
            item_id=i

# Remove a disciplina
    disciplina = disciplinas[item_id]
    if disciplina is not None:
        disciplinas.pop(item_id)
    return disciplinas


if __name__ == '__main__':
    uvicorn.run(app, port=8081)
