import pytest
from meu_codigo.pedido import *

def test_calcular_desconto_caso Normal():
    resultado = calcular_desconto(100, "DEZ")
    assert resultado == 90

def test_calcular_desconto_caso_NuloCupom():
    resultado = calcular_desconto(100, None)
    assert resultado == 100

def test_calcular_desconto_caso_ErrorTipoCupom():
    with pytest.raises(TypeError):
        calcular_desconto(100, "abc")

def test_calcular_desconto_casoValorInvalido():
    with pytest.raises(TypeError):
        calcular_desconto(-100, "DEZ")