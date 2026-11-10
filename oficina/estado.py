import json, sqlite3, time

class Estado:
    def __init__(self, ruta="oficina.db"):
        self.db = sqlite3.connect(ruta)
        for q in [
            "create table if not exists notas(id integer primary key, ts real, cuenta text, clave text, datos text)",
            "create table if not exists cola(id integer primary key, cuenta text, plataforma text, programada real, estado text, datos text)",
            "create table if not exists publicaciones(id integer primary key, cuenta text, plataforma text, post_id text, ts real, hora int, titulo text, caption text)",
            "create table if not exists metricas(id integer primary key, pub_id int, ts real, vistas int, likes int, comentarios int, compartidos int, seguidores int)",
            "create table if not exists respondidos(comentario_id text primary key)",
            "create table if not exists peticiones(id integer primary key, ts real, tema text, dominio text)"]:
            self.db.execute(q)
        for col in ("dominio text", "tema text"):
            try: self.db.execute(f"alter table publicaciones add column {col}")
            except sqlite3.OperationalError: pass
        self.db.commit()

    def q(self, sql, args=()):
        c = self.db.execute(sql, args); self.db.commit(); return c

    def nota(self, cuenta, clave, datos):
        self.q("insert into notas(ts,cuenta,clave,datos) values(?,?,?,?)", (time.time(), cuenta, clave, json.dumps(datos, ensure_ascii=False)))

    def ultima_nota(self, cuenta, clave):
        f = self.q("select datos, ts from notas where cuenta=? and clave=? order by id desc limit 1", (cuenta, clave)).fetchone()
        return (json.loads(f[0]), f[1]) if f else (None, 0)

    def encolar(self, cuenta, plataforma, programada, datos):
        self.q("insert into cola(cuenta,plataforma,programada,estado,datos) values(?,?,?,?,?)",
               (cuenta, plataforma, programada, "pendiente", json.dumps(datos, ensure_ascii=False)))

    def pendientes(self, ahora):
        return [(i, c, p, json.loads(d)) for i, c, p, d in self.q(
            "select id,cuenta,plataforma,datos from cola where estado='pendiente' and programada<=?", (ahora,)).fetchall()]

    def marcar(self, id_, estado):
        self.q("update cola set estado=? where id=?", (estado, id_))

    def reprogramar(self, id_, programada, datos):
        """Deja la fila en 'pendiente' pero para más tarde (reintento con backoff) guardando el nº de intentos en datos."""
        self.q("update cola set programada=?, datos=? where id=?", (programada, json.dumps(datos, ensure_ascii=False), id_))

    def registrar_publicacion(self, cuenta, plat, post_id, hora, titulo, caption, dominio=None, tema=None):
        return self.q("insert into publicaciones(cuenta,plataforma,post_id,ts,hora,titulo,caption,dominio,tema) values(?,?,?,?,?,?,?,?,?)",
                      (cuenta, plat, str(post_id), time.time(), hora, titulo, caption, dominio, tema)).lastrowid

    def publicaciones(self, cuenta=None, desde=0):
        sql = "select id,cuenta,plataforma,post_id,ts,hora,titulo,caption from publicaciones where ts>=?"
        args = [desde]
        if cuenta:
            sql += " and cuenta=?"; args.append(cuenta)
        return self.q(sql + " order by ts desc", args).fetchall()

    def guardar_metricas(self, pub_id, m):
        self.q("insert into metricas(pub_id,ts,vistas,likes,comentarios,compartidos,seguidores) values(?,?,?,?,?,?,?)",
               (pub_id, time.time(), m.get("vistas", 0), m.get("likes", 0), m.get("comentarios", 0), m.get("compartidos", 0), m.get("seguidores", 0)))

    def ultima_metrica(self, pub_id):
        return self.q("select vistas,likes,comentarios,compartidos,seguidores,ts from metricas where pub_id=? order by id desc limit 1", (pub_id,)).fetchone()
