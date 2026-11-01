import hashlib
import json
import sys

from tools import verificar_repositorios_reels as verificador


def preparar(tmp_path, monkeypatch, alterado=False, licencia=True):
    carpeta=tmp_path/'skill';carpeta.mkdir();(carpeta/'SKILL.md').write_text('Skill local',encoding='utf-8')
    origen=tmp_path/'LICENSE';origen.write_text('MIT License\nPermission is hereby granted, free of charge',encoding='utf-8')
    (tmp_path/'config').mkdir()
    fila={'nombre':'prueba','path':str(carpeta),'tipo':'skill','sha256_skill':'alterado' if alterado else hashlib.sha256((carpeta/'SKILL.md').read_bytes()).hexdigest(),
          'licencia_origen_local':str(origen if licencia else tmp_path/'ausente'),'skill_origen_verificado':True}
    (tmp_path/'config/repositorios-20261031.json').write_text(json.dumps([fila]),encoding='utf-8')
    monkeypatch.setattr(verificador,'RAIZ',tmp_path);monkeypatch.setattr(sys,'argv',['verificador'])
    monkeypatch.setattr(verificador,'git',lambda *_: (_ for _ in ()).throw(AssertionError('Una skill no requiere Git')))


def test_skill_local_no_se_confunde_con_clon_git(tmp_path,monkeypatch,capsys):
    preparar(tmp_path,monkeypatch);verificador.main();assert '1 sin problemas' in capsys.readouterr().out


def test_skill_alterada_sigue_como_observacion(tmp_path,monkeypatch,capsys):
    preparar(tmp_path,monkeypatch,alterado=True);verificador.main();assert 'huella distinta' in capsys.readouterr().out


def test_licencia_ausente_no_se_da_por_verificada(tmp_path,monkeypatch,capsys):
    preparar(tmp_path,monkeypatch,licencia=False);verificador.main();assert 'licencia de origen no verificada' in capsys.readouterr().out
