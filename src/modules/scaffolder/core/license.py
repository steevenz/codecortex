"""
License value object — encapsulates license selection and content generation.

:project: CodeCortex
:package: Modules.Scaffolder.Core.License
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Optional

from .constants import LicenseIdentifier

@dataclass(frozen=True)
class License:
    """Immutable value object representing a license selection.

    Encapsulates license identifier and provides content generation
    for the LICENSE file in generated projects.
    """

    identifier: LicenseIdentifier

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_string(cls, value: str) -> License:
        """Resolve a license identifier from a string (case-insensitive)."""
        normalised = value.strip()
        for member in LicenseIdentifier:
            if member.value.lower() == normalised.lower():
                return cls(identifier=member)
        return cls(identifier=LicenseIdentifier.NONE)

    @classmethod
    def none(cls) -> License:
        return cls(identifier=LicenseIdentifier.NONE)

    # ------------------------------------------------------------------
    # Content generation
    # ------------------------------------------------------------------

    def render_content(self, author: str, year: int) -> Optional[str]:
        """Generate LICENSE file content.

        Returns:
            License text, or ``None`` when identifier is NONE.
        """
        generators = {
            LicenseIdentifier.MIT: self._mit,
            LicenseIdentifier.APACHE_2: self._apache2,
            LicenseIdentifier.GPL_3: self._gpl3,
            LicenseIdentifier.BSD_3: self._bsd3,
            LicenseIdentifier.COMMERCIAL_COMPANY: self._commercial_company,
            LicenseIdentifier.COMMERCIAL_PERSONAL: self._commercial_personal,
            LicenseIdentifier.PRIVATE_COMPANY: self._private_company,
            LicenseIdentifier.PRIVATE_PERSONAL: self._private_personal,
        }

        generator = generators.get(self.identifier)
        if generator is None:
            return None
        return generator(author, year)

    @property
    def is_none(self) -> bool:
        return self.identifier == LicenseIdentifier.NONE

    # ------------------------------------------------------------------
    # License templates
    # ------------------------------------------------------------------

    @staticmethod
    def _mit(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            MIT License

            Copyright (c) {year} {author}

            Permission is hereby granted, free of charge, to any person obtaining a copy
            of this software and associated documentation files (the "Software"), to deal
            in the Software without restriction, including without limitation the rights
            to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
            copies of the Software, and to permit persons to whom the Software is
            furnished to do so, subject to the following conditions:

            The above copyright notice and this permission notice shall be included in all
            copies or substantial portions of the Software.

            THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
            IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
            FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
            AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
            LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
            OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
            SOFTWARE.
        """)

    @staticmethod
    def _apache2(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            Apache License
            Version 2.0, January 2004
            http://www.apache.org/licenses/

            Copyright {year} {author}

            Licensed under the Apache License, Version 2.0 (the "License");
            you may not use this file except in compliance with the License.
            You may obtain a copy of the License at

                http://www.apache.org/licenses/LICENSE-2.0

            Unless required by applicable law or agreed to in writing, software
            distributed under the License is distributed on an "AS IS" BASIS,
            WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
            See the License for the specific language governing permissions and
            limitations under the License.
        """)

    @staticmethod
    def _gpl3(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            Copyright (c) {year} {author}

            This program is free software: you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation, either version 3 of the License, or
            (at your option) any later version.

            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with this program. If not, see <https://www.gnu.org/licenses/>.
        """)

    @staticmethod
    def _bsd3(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            BSD 3-Clause License

            Copyright (c) {year} {author}
            All rights reserved.

            Redistribution and use in source and binary forms, with or without
            modification, are permitted provided that the following conditions are met:

            1. Redistributions of source code must retain the above copyright notice,
               this list of conditions and the following disclaimer.
            2. Redistributions in binary form must reproduce the above copyright notice,
               this list of conditions and the following disclaimer in the documentation
               and/or other materials provided with the distribution.
            3. Neither the name of the copyright holder nor the names of its contributors
               may be used to endorse or promote products derived from this software
               without specific prior written permission.

            THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
            AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
            IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
            ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
            LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
            CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
            SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
            INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
            CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
            ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
            THE POSSIBILITY OF SUCH DAMAGE.
        """)

    @staticmethod
    def _commercial_company(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            Commercial License

            Copyright (c) {year} {author}. All rights reserved.

            This software and its documentation are proprietary to {author}.
            Unauthorized copying, modification, distribution, or use of this software,
            via any medium, is strictly prohibited.

            This software is provided under a commercial license agreement.
            Contact {author} for licensing terms.
        """)

    @staticmethod
    def _commercial_personal(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            Personal Commercial License

            Copyright (c) {year} {author}. All rights reserved.

            This software is licensed for personal commercial use by {author} only.
            Redistribution or sublicensing is not permitted without explicit written
            permission from the author.
        """)

    @staticmethod
    def _private_company(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            Private & Confidential

            Copyright (c) {year} {author}. All rights reserved.

            This software is the confidential and proprietary information of {author}.
            It is intended solely for internal use and may not be disclosed, copied,
            or distributed to any third party without prior written consent.
        """)

    @staticmethod
    def _private_personal(author: str, year: int) -> str:
        return textwrap.dedent(f"""\
            Private License

            Copyright (c) {year} {author}. All rights reserved.

            This software is for personal and private use only.
            No part of this software may be reproduced, distributed, or transmitted
            in any form without the prior written permission of the author.
        """)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __str__(self) -> str:  # noqa: D105
        return self.identifier.value
