#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2021 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
from unittest.mock import MagicMock

import pynguin.assertion.fieldassertion as fa
from pynguin.assertion import assertionvisitor as av
from pynguin.testcase import testcase as tc


class FooAssertion(fa.FieldAssertion):
    def accept(self, visitor: av.AssertionVisitor) -> None:
        pass  # pragma: no cover

    def clone(self, new_test_case: tc.TestCase, offset: int) -> fa.FieldAssertion:
        pass  # pragma: no cover


def test_accept():
    visitor = MagicMock()
    assertion = fa.FieldAssertion(MagicMock(), 1337, 'field')
    assertion.accept(visitor)
    visitor.visit_field_assertion.assert_called_with(assertion)


def test_clone():
    source = MagicMock()
    cloned_ref = MagicMock()
    source.clone.return_value = cloned_ref
    assertion = fa.FieldAssertion(source, 1337, 'field')
    new_test_case = MagicMock()
    cloned = assertion.clone(new_test_case, 20)
    source.clone.assert_called_with(new_test_case, 20)
    assert cloned.source == cloned_ref
    assert cloned.value == 1337
    assert cloned.field == 'field'
    assert cloned.owners is None


def test_eq():
    var = MagicMock()
    assert FooAssertion(var, True, 'foo') == FooAssertion(var, True, 'foo')


def test_neq():
    assert FooAssertion(MagicMock(), True, 'foo') != FooAssertion(MagicMock(),
                                                                  True, 'foo')


def test_hash():
    var = MagicMock()
    assert hash(FooAssertion(var, True, 'foo')) == hash(FooAssertion(var, True, 'foo'))


def test_neq_hash():
    assert hash(FooAssertion(MagicMock(), True, 'foo')) != hash(
        FooAssertion(MagicMock(), True, 'foo')
    )
