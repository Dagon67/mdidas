# Minhas cores ideais – Passo a passo

## O que foi implementado

- **Backend Python** (pasta `backend/`): API FastAPI que recebe 3–4 fotos, faz pré-processamento, segmentação (rosto/pele/cabelo), extração de características em LAB/HSV, classificação por regras (subtom, valor, croma, contraste, estação) e gera paletas + recomendações textuais.
- **Página no app** (`cores.html`): instruções de fotos, upload, chamada ao backend e exibição do perfil cromático, paletas (principal, neutra, destaque) e recomendações.
- **Ícone na home**: "Minhas cores ideais" leva para `cores.html`.

---

## 1. Como usar (usuário final)

1. **Entrar no app**  
   Faça login com Google na aplicação.

2. **Abrir Minhas cores ideais**  
   Na página inicial, toque/clique no ícone **Minhas cores ideais** (paleta de cores).

3. **Ler as instruções**  
   Na tela você verá:
   - Rosto: sem maquiagem, luz natural difusa, fundo neutro.
   - Parte interna do braço: para subtom.
   - Cabelo: próximo à raiz, sem luz direta.
   - Parte externa do braço (opcional).
   - Sem roupa colorida, filtros, flash ou luz artificial; se possível, objeto neutro (folha branca ou cartão cinza) perto do rosto.

4. **Tirar as fotos**  
   Tire as 3 fotos obrigatórias (e, se quiser, a 4ª) seguindo essas regras.

5. **Enviar**  
   Selecione cada foto no formulário (1. Rosto, 2. Braço interno, 3. Cabelo, 4. Braço externo opcional) e clique em **Analisar minhas cores**.

6. **Ver o resultado**  
   Após o processamento aparecem:
   - **Perfil cromático**: estação (ex.: Primavera, Verão), subtom (quente/frio/neutro/oliva), valor (claridade), croma (saturação), contraste.
   - **Paletas**: cores em hex (principal, neutra, destaque) com amostras visuais.
   - **Recomendações**: textos explicando quais cores harmonizam e por quê.

---

## 2. Como rodar (desenvolvedor)

### 2.1 Backend (Python)

1. **Requisitos**  
   Python 3.10+ recomendado.

2. **Ambiente e dependências**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

3. **Subir a API**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   A API fica em `http://localhost:8000`.  
   Endpoint de análise: `POST http://localhost:8000/analisar` com `multipart/form-data`:  
   `rosto`, `braco_interno`, `cabelo` (obrigatórios), `braco_externo` (opcional).

4. **Configurar a URL no frontend**  
   Em `cores.html`, defina a URL do backend:
   ```javascript
   var API_CORES_URL = "http://localhost:8000";
   ```
   Em produção, use a URL pública do backend (ex.: Cloud Run):  
   `var API_CORES_URL = "https://sua-api.run.app";`

### 2.2 Frontend (app atual)

- O app continua sendo servido como está (Firebase Hosting ou abrindo os HTMLs).
- A página **Minhas cores ideais** chama o backend na URL configurada em `API_CORES_URL`.
- Se `API_CORES_URL` estiver vazio, a página mostra um aviso pedindo para configurar a URL.

### 2.3 Deploy do backend (ex.: Google Cloud Run)

1. Na pasta `backend/`, crie um `Dockerfile` (ex.:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```
2. Build e deploy no Cloud Run (ou outro provedor).
3. Defina `API_CORES_URL` em `cores.html` com a URL do serviço (ex.: `https://colorimetria-xxx.run.app`).

---

## 3. Resumo do fluxo técnico

1. **Entrada**: 3–4 imagens (rosto, braço interno, cabelo, braço externo opcional).
2. **Pré-processamento**: balanço de branco, normalização de exposição, conversão LAB/HSV.
3. **Segmentação**: rosto (MediaPipe), pele (HSV + máscara facial), cabelo (região escura superior).
4. **Extração**: descarte de outliers, média/mediana LAB, k-means para clusters dominantes.
5. **Variáveis**: subtom (quente/frio/neutro/oliva), valor, croma, contraste (pele × cabelo).
6. **Classificação**: regras → estação (Primavera/Verão/Outono/Inverno + suave/intenso).
7. **Saída**: JSON com perfil, paletas (principal/neutra/destaque) em LAB+HEX e recomendações textuais.

---

## 4. Arquivos principais

| Caminho | Função |
|--------|--------|
| `backend/main.py` | API FastAPI, endpoint `/analisar` |
| `backend/processing/preprocess.py` | Balanço de branco, exposição, LAB/HSV |
| `backend/processing/segment.py` | Rosto, pele, cabelo (MediaPipe + OpenCV) |
| `backend/processing/extract.py` | Média, mediana, k-means, descarte outliers |
| `backend/processing/classify.py` | Subtom, valor, croma, contraste, estação |
| `backend/processing/recommend.py` | Paletas e textos de recomendação |
| `cores.html` | Página no app: instruções, upload, resultado |
| `index.html` | Ícone "Minhas cores ideais" → `cores.html` |

Se quiser, na próxima etapa podemos ajustar regras de classificação, paletas ou textos de recomendação.
