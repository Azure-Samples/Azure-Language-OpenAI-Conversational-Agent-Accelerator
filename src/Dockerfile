FROM mcr.microsoft.com/cbl-mariner/base/nodejs:18 AS build-ui

WORKDIR /app

COPY frontend/src/ /app/src
COPY frontend/package.json /app
COPY frontend/vite.config.js /app
COPY frontend/index.html /app

RUN npm install
RUN npm run build

FROM mcr.microsoft.com/azurelinux/base/python:3

WORKDIR /app

COPY --from=build-ui /app/dist /app/dist

COPY backend/src/ /app
COPY backend/requirements.txt /app

RUN pip install -r requirements.txt

EXPOSE 80

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
