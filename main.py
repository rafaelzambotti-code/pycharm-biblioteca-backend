from flask import Flask, render_template, request, session, redirect, send_from_directory, send_file
import fdb
from flask_bcrypt import Bcrypt
from fpdf import FPDF

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config["UPLOAD_FOLDER"] = "uploads"

app.config['SECRET_KEY'] = 'chave_turma_a'

host = "localhost"
database = r"C:\Users\Rafael\Downloads\BANCO_BIBLIOTECA.FDB"
user = "sysdba"
password = "SYSDBA"

con = fdb.connect(database=database, user=user, password=password, host=host)


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        senha = bcrypt.generate_password_hash(senha).decode('utf-8')


        cursor = con.cursor()
        cursor.execute("SELECT MAX(ID_USUARIO) FROM USUARIOS")
        resultado = cursor.fetchone()

        if resultado[0] is None:
            id_usuario = 1
        else:
            id_usuario = resultado[0] + 1

        cursor.execute("""
                  INSERT INTO USUARIOS
                  (ID_USUARIO, NOME, EMAIL, SENHA, TENTATIVAS, BLOQUEADO)
                  VALUES (?, ?, ?, ?, ?, ?)
              """, (id_usuario, nome, email, senha, 0, 0))

        con.commit()

        return "Cadastro realizado com sucesso!"

    return render_template("cadastro.html")

@app.route("/login", methods=["GET", "POST"])
def fazer_login():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        cursor = con.cursor()

        cursor.execute("""
            SELECT ID_USUARIO, SENHA, TENTATIVAS, BLOQUEADO
            FROM USUARIOS
            WHERE NOME = ? AND EMAIL = ?
        """, (nome, email))

        usuario = cursor.fetchone()

        if usuario:
            id_usuario = usuario[0]
            senha_hash = usuario[1]
            tentativas = usuario[2]
            bloqueado = usuario[3]

            if bloqueado == 1:
                return "Usuário bloqueado!"

            if bcrypt.check_password_hash(senha_hash, senha):
                session["id_usuario"] = id_usuario
                return redirect("/inicio")

            else:
                tentativas = tentativas + 1

                if tentativas >= 3:
                    cursor.execute("""
                        UPDATE USUARIOS
                        SET TENTATIVAS = ?, BLOQUEADO = 1
                        WHERE ID_USUARIO = ?
                    """, (tentativas, id_usuario))

                    con.commit()

                    return "Usuário bloqueado!"

                else:
                    cursor.execute("""
                        UPDATE USUARIOS
                        SET TENTATIVAS = ?
                        WHERE ID_USUARIO = ?
                    """, (tentativas, id_usuario))

                    con.commit()

                    return "Senha incorreta!"

        return "Cadastro incorreto!"

    return render_template("login.html")

@app.route("/inicio")
def inicio():
    cursor = con.cursor()

    cursor.execute("""
        SELECT ID_LIVRO, NOME, AUTOR, ANO_PUBLICACAO
        FROM LIVROS
        ORDER BY ID_LIVRO ASC""")

    livros = cursor.fetchall()

    return render_template("inicio.html", livros=livros)

@app.route("/logout")
def logout():
    session.pop("id_usuario", None)
    return redirect("/inicio")

@app.route("/uploads/<nome_imagem>")
def mostrar_imagem(nome_imagem):
    return send_from_directory("uploads", nome_imagem)

@app.route("/novo", methods=["GET", "POST"])
def novo():
    if "id_usuario" not in session:
        return redirect("/")

    if request.method == "POST":
        nome = request.form["nome"]
        autor = request.form["autor"]
        ano = request.form["ano"]
        imagem = request.files["imagem"]


        cursor = con.cursor()

        cursor.execute("SELECT MAX(ID_LIVRO) FROM LIVROS")
        resultado = cursor.fetchone()

        if resultado[0] is None:
            id_livro = 1
        else:
            id_livro = resultado[0] + 1

        nome_imagem = str(id_livro) + ".jpg"
        imagem.save("uploads/" + nome_imagem)

        cursor.execute("""
            INSERT INTO LIVROS
            (ID_LIVRO, NOME, AUTOR, ANO_PUBLICACAO)
            VALUES (?, ?, ?, ?)
        """, (id_livro, nome, autor, ano, nome_imagem))

        con.commit()

        return redirect("/inicio")

    return render_template("novo.html")

@app.route("/editar/<int:id_livro>", methods=["GET", "POST"])
def editar(id_livro):

    if "id_usuario" not in session:
        return redirect("/")

    cursor = con.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        autor = request.form["autor"]
        ano = request.form["ano"]

        imagem = request.files["imagem"]

        if imagem.filename:
            nome_imagem = str(id_livro) + ".jpg"
            imagem.save("uploads/" + nome_imagem)

        cursor.execute("""
            UPDATE LIVROS
            SET NOME = ?, AUTOR = ?, ANO_PUBLICACAO = ?
            WHERE ID_LIVRO = ?
        """, (nome, autor, ano, id_livro))

        con.commit()

        return redirect("/inicio")

    cursor.execute("""
        SELECT ID_LIVRO, NOME, AUTOR, ANO_PUBLICACAO
        FROM LIVROS
        WHERE ID_LIVRO = ?
    """, (id_livro,))

    livro = cursor.fetchone()

    return render_template("editar.html", livro=livro)

@app.route("/excluir/<int:id_livro>")
def excluir(id_livro):
    if "id_usuario" not in session:
        return redirect("/")

    cursor = con.cursor()

    cursor.execute("""
        DELETE FROM LIVROS
        WHERE ID_LIVRO = ?
    """, (id_livro,))

    con.commit()

    return redirect("/inicio")

@app.route("/pdf")
def gerar_pdf():
    if "id_usuario" not in session:
        return redirect("/")

    cursor = con.cursor()

    cursor.execute("""
        SELECT ID_LIVRO, NOME, AUTOR, ANO_PUBLICACAO
        FROM LIVROS
        ORDER BY ID_LIVRO ASC""")

    livros = cursor.fetchall()

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatório da Biblioteca", ln=True, align="C")

    pdf.ln(10)

    for livro in livros:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Código: " + str(livro[0]), ln=True)

        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, "Nome: " + livro[1], ln=True)
        pdf.cell(0, 10, "Autor: " + livro[2], ln=True)
        pdf.cell(0, 10, "Ano de publicação: " + str(livro[3]), ln=True)

        try:
            pdf.image("uploads/" + str(livro[0]) + ".jpg", w=40)
            pdf.ln(5)
        except:
            print("Livro sem imagem")

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Total de livros: " + str(len(livros)), ln=True)

    pdf.output("relatorio.pdf")

    return send_file("relatorio.pdf", as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True)