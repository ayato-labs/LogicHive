import pytest
from orchestrator import extract_dependencies, do_list_async

def test_extract_dependencies_python():
    code = """
import os
import sys
from pandas import DataFrame
import numpy as np
from datetime import datetime
"""
    deps = extract_dependencies(code, "python")
    # os, sys, datetime are stdlib -> excluded
    assert "pandas" in deps
    assert "numpy" in deps
    assert len(deps) == 2

def test_extract_dependencies_js():
    code = """
import { something } from 'lodash';
const fs = require('fs');
import axios from "axios";
const myLocal = require('./local'); // Should be excluded
import '@types/node';
"""
    deps = extract_dependencies(code, "javascript")
    # fs is stdlib -> excluded
    assert "lodash" in deps
    assert "axios" in deps
    assert "@types/node" in deps
    assert "local" not in deps
    assert len(deps) == 3

@pytest.mark.asyncio
async def test_do_list_async_integration(test_db):
    """
    Test do_list_async which depends on storage.
    Since it doesn't call LLM, it's a pure unit/local-integration test.
    """
    from storage.sqlite_api import sqlite_storage
    await sqlite_storage.upsert_function({"name": "list_me", "project": "list_proj", "code": "pass", "code_hash": "h"})
    
    results = await do_list_async(project="list_proj")
    assert len(results) == 1
    assert results[0]["name"] == "list_me"
