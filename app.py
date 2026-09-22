from flask import Flask, request, redirect, render_template
from banco import conectar

app = Flask(__name__)


@app.get("/")
def inicio():
    return render_template("index.html")


@app.post("/cadastrar")
def cadastrar():
    dados = (
        request.form.get("ativo", "").strip(),
        request.form.get("numero_serie", "").strip(),
        request.form.get("categoria", "").strip(),
        request.form.get("status", "").strip(),
        request.form.get("matricula", "").strip(),
        request.form.get("data_garantia") or None,
        request.form.get("departamento", "").strip(),
        request.form.get("responsavel", "").strip(),
        request.form.get("empresa", "").strip(),
    )

    if not dados[0] or not dados[1]:
        return "Preencha o ativo e o número de série.", 400

    conexao = conectar()
    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO ativo (
                ativo,
                numero_serie,
                categoria,
                status,
                matricula,
                data_garantia,
                departamento,
                responsavel,
                empresa,
                cadastrado_em
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            dados,
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()

        conexao.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=False)