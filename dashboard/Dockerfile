FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8591
CMD ["streamlit", "run", "app.py", "--server.port=8591", "--server.address=0.0.0.0"]