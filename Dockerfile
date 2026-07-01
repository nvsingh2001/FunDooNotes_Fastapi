FROM python:3.13-slim
WORKDIR /FunDooNotes

COPY . . 
EXPOSE 8000

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m fundoonotes \
  && chown -R fundoonotes:fundoonotes /FunDooNotes

USER fundoonotes

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]




