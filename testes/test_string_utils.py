import pytest
from meu_codigo.string_utils import *

def test_inverter_texto_caso_normao():
    assert inverter_texto("Python") == "nohtyP"

def test_inverter_texto_caso_vazio():
    assert inverter_texto("") == ""

def test_inverter_texto_caso_error_tipoint():
    with pytest.raises(TypeError):
        inverter_texto(123)

def test_inverter_texto_caso_error_typestring():
    with pytest.raises(TypeError):
        inverter_texto(None)