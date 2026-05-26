import pytest
from meu_codigo.usuarios import validar_senha

def test_validar_senha_caso_normal():
    assert validar_senha("minhasenhasem8letros") is True

def test_validar_senha_caso_falta_caracteres_especiais():
    assert validar_senha("senhasem9letra") is False

def test_validar_senha_caso_falta_letras():
    assert validar_senha("SENHASEMNUMERO") is False

def test_validar_senha_caso_vazio():
    assert validar_senha("") is False

def test_validar_senha_caso_nulo():
    with pytest.raises(TypeError):
        validar_senha(None)