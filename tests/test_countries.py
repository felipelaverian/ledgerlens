import pytest

from ledgerlens.countries import chile_rut_is_valid, get_profile, peru_ruc_is_valid


@pytest.mark.parametrize(("ruc", "valid"), [("20555555556", True), ("20555555551", False), ("2055555555", False)])
def test_peru_ruc(ruc, valid):
    assert peru_ruc_is_valid(ruc) is valid


@pytest.mark.parametrize(("rut", "valid"), [("760864285", True), ("760864284", False), ("12345678K", False)])
def test_chile_rut(rut, valid):
    assert chile_rut_is_valid(rut) is valid


def test_unknown_country_lists_the_available_ones():
    with pytest.raises(ValueError, match="Available: GENERIC"):
        get_profile("XX")


def test_profile_lookup_is_case_insensitive():
    assert get_profile("pe").tax_id_name == "RUC"
