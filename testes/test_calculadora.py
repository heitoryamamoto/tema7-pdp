import pytest
from meu_codigo.calculadora import *

from meuCodigo.calculadora import *

def test_soma_caso_normal():
    assert soma(2, 3) == 5

def test_soma_caso_borda_negativo():
    with pytest.raises(TypeError):
        soma(-1, 3)

def test_soma_caso_borda_negativo_e_positivo():
    comeca = soma(-1, 3)
    assert soma(comeca, -2) == comeca + (-2)

def test_soma_caso_tipo_incorreto():
    with pytest.raises(TypeError):
        soma('a', 3)

def test_soma_caso_tipo_incorreto_e_outro():
    comeca = soma(1, 'b')
    assert soma(comeca, 4) == comeca + 4