#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Desc   : unittest of Role
import pytest

from metagpt.llm import HumanProvider
from metagpt.roles.role import Role


def test_role_desc():
    role = Role(profile="Sales", desc="Best Seller")
    assert role.profile == "Sales"
    assert role.desc == "Best Seller"


def test_role_human():
    role = Role(is_human=True)
    assert isinstance(role.llm, HumanProvider)


if __name__ == "__main__":
    pytest.main([__file__, "-s"])
