from __future__ import annotations

import ctypes
import ctypes.util
from ctypes import c_bool, c_char_p, c_long, c_uint32, c_void_p


InputSourceItem = dict[str, str]


class MacInputSourceManager:
    CFStringRef = c_void_p
    CFArrayRef = c_void_p
    CFDictionaryRef = c_void_p
    CFTypeRef = c_void_p
    TISInputSourceRef = c_void_p
    kCFStringEncodingUTF8 = 0x08000100

    def __init__(self) -> None:
        self._CF = None
        self._HT = None
        self._layout_type = None
        self._input_mode_type = None
        self._load_frameworks()
        self._bind_cf()
        self._bind_ht()
        self._load_cf_constants()

    @staticmethod
    def _load_framework(name: str, paths: list[str]) -> ctypes.CDLL:
        lib = ctypes.util.find_library(name)
        if lib:
            try:
                return ctypes.CDLL(lib)
            except OSError:
                pass

        last_error = None
        for path in paths:
            try:
                return ctypes.CDLL(path)
            except OSError as exc:
                last_error = exc

        raise last_error or OSError(f'Cannot load framework {name}')

    def _load_frameworks(self) -> None:
        self._HT = self._load_framework(
            'HIToolbox',
            [
                '/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework/HIToolbox',
                '/System/Library/Frameworks/ApplicationServices.framework/Frameworks/HIToolbox.framework/HIToolbox',
            ],
        )
        self._CF = self._load_framework(
            'CoreFoundation',
            ['/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'],
        )

    def _bind_cf(self) -> None:
        core_foundation = self._CF
        core_foundation.CFStringGetCString.argtypes = [self.CFStringRef, c_char_p, c_long, c_uint32]
        core_foundation.CFStringGetCString.restype = c_bool
        core_foundation.CFArrayGetCount.argtypes = [self.CFArrayRef]
        core_foundation.CFArrayGetCount.restype = c_long
        core_foundation.CFArrayGetValueAtIndex.argtypes = [self.CFArrayRef, c_long]
        core_foundation.CFArrayGetValueAtIndex.restype = c_void_p
        core_foundation.CFRelease.argtypes = [c_void_p]
        core_foundation.CFRelease.restype = None

    def _bind_ht(self) -> None:
        hitoolbox = self._HT
        hitoolbox.TISCreateInputSourceList.argtypes = [self.CFDictionaryRef, c_bool]
        hitoolbox.TISCreateInputSourceList.restype = self.CFArrayRef
        hitoolbox.TISGetInputSourceProperty.argtypes = [self.TISInputSourceRef, c_void_p]
        hitoolbox.TISGetInputSourceProperty.restype = self.CFTypeRef
        hitoolbox.TISSelectInputSource.argtypes = [self.TISInputSourceRef]
        hitoolbox.TISSelectInputSource.restype = c_uint32

    def _optional_cf_constant(self, name: str) -> c_void_p | None:
        try:
            return self.CFStringRef.in_dll(self._HT, name)
        except ValueError:
            return None

    def _load_cf_constants(self) -> None:
        self.kTISPropertyInputSourceID = self._optional_cf_constant('kTISPropertyInputSourceID')
        self.kTISPropertyInputSourceType = self._optional_cf_constant('kTISPropertyInputSourceType')
        self.kTISPropertyLocalizedName = self._optional_cf_constant('kTISPropertyLocalizedName')
        self.kTISPropertyInputSourceIsSelected = self._optional_cf_constant('kTISPropertyInputSourceIsSelected')
        self.kTISPropertyPrimaryLanguage = self._optional_cf_constant('kTISPropertyPrimaryLanguage')
        self.kTISPropertyInputSourceLanguages = self._optional_cf_constant('kTISPropertyInputSourceLanguages')
        self.kTISTypeKeyboardLayout = self._optional_cf_constant('kTISTypeKeyboardLayout')
        self.kTISTypeKeyboardInputMode = self._optional_cf_constant('kTISTypeKeyboardInputMode')

        self._layout_type = self._cfstring_to_py(self.kTISTypeKeyboardLayout) if self.kTISTypeKeyboardLayout else ''
        self._input_mode_type = (
            self._cfstring_to_py(self.kTISTypeKeyboardInputMode) if self.kTISTypeKeyboardInputMode else ''
        )

    def _cfstring_to_py(self, value: CFStringRef | None) -> str:
        if not value:
            return ''

        buffer = ctypes.create_string_buffer(1024)
        ok = self._CF.CFStringGetCString(value, buffer, len(buffer), self.kCFStringEncodingUTF8)
        if not ok:
            return ''

        raw_value = buffer.value
        if raw_value is None:
            return ''

        return bytes(raw_value).decode('utf-8')

    def _create_input_source_array(self) -> CFArrayRef | None:
        return self._HT.TISCreateInputSourceList(None, True)

    def _read_lang(self, source: TISInputSourceRef) -> str:
        if self.kTISPropertyInputSourceLanguages:
            languages_ref = self._HT.TISGetInputSourceProperty(source, self.kTISPropertyInputSourceLanguages)
            if languages_ref:
                array_ref = self.CFArrayRef(languages_ref)
                count = self._CF.CFArrayGetCount(array_ref)
                if count > 0:
                    first = self.CFStringRef(self._CF.CFArrayGetValueAtIndex(array_ref, 0))
                    lang = self._cfstring_to_py(first)
                    if lang:
                        return lang

        if self.kTISPropertyPrimaryLanguage:
            lang_ref = self._HT.TISGetInputSourceProperty(source, self.kTISPropertyPrimaryLanguage)
            if lang_ref:
                return self._cfstring_to_py(self.CFStringRef(lang_ref))

        return ''

    def list_sources(self, include_types: tuple[str, ...] | None = ('layout', 'inputmode')) -> list[InputSourceItem]:
        array_ref = self._create_input_source_array()
        if not array_ref:
            raise RuntimeError('Failed to get input sources list')

        items: list[InputSourceItem] = []
        try:
            count = self._CF.CFArrayGetCount(array_ref)
            for index in range(count):
                source = self.TISInputSourceRef(self._CF.CFArrayGetValueAtIndex(array_ref, index))
                type_ref = (
                    self._HT.TISGetInputSourceProperty(source, self.kTISPropertyInputSourceType)
                    if self.kTISPropertyInputSourceType
                    else None
                )
                name_ref = (
                    self._HT.TISGetInputSourceProperty(source, self.kTISPropertyLocalizedName)
                    if self.kTISPropertyLocalizedName
                    else None
                )
                id_ref = (
                    self._HT.TISGetInputSourceProperty(source, self.kTISPropertyInputSourceID)
                    if self.kTISPropertyInputSourceID
                    else None
                )
                selected_ref = (
                    self._HT.TISGetInputSourceProperty(source, self.kTISPropertyInputSourceIsSelected)
                    if self.kTISPropertyInputSourceIsSelected
                    else None
                )

                type_name = self._cfstring_to_py(self.CFStringRef(type_ref)) if type_ref else ''
                if self._layout_type and type_name == self._layout_type:
                    human_type = 'layout'
                elif self._input_mode_type and type_name == self._input_mode_type:
                    human_type = 'inputmode'
                else:
                    human_type = 'other'

                if include_types and human_type not in include_types:
                    continue

                items.append(
                    {
                        'id': self._cfstring_to_py(self.CFStringRef(id_ref)) if id_ref else '',
                        'name': self._cfstring_to_py(self.CFStringRef(name_ref)) if name_ref else '',
                        'type': human_type,
                        'lang': self._read_lang(source),
                        'selected': '1' if selected_ref else '0',
                    }
                )
            return items
        finally:
            self._CF.CFRelease(array_ref)

    def switch_by_id(self, source_id: str) -> None:
        array_ref = self._create_input_source_array()
        if not array_ref:
            raise RuntimeError('Failed to get input sources list')

        try:
            count = self._CF.CFArrayGetCount(array_ref)
            for index in range(count):
                source = self.TISInputSourceRef(self._CF.CFArrayGetValueAtIndex(array_ref, index))
                source_id_ref = (
                    self._HT.TISGetInputSourceProperty(source, self.kTISPropertyInputSourceID)
                    if self.kTISPropertyInputSourceID
                    else None
                )
                if source_id_ref and self._cfstring_to_py(self.CFStringRef(source_id_ref)) == source_id:
                    status = self._HT.TISSelectInputSource(source)
                    if status != 0:
                        raise OSError(status, f'TISSelectInputSource error {status}')
                    return
        finally:
            self._CF.CFRelease(array_ref)

        raise ValueError(f"Input source with ID '{source_id}' was not found")

    def switch_by_language(self, lang_code: str) -> None:
        for item in self.list_sources(include_types=('layout', 'inputmode')):
            if item['lang'] == lang_code:
                self.switch_by_id(item['id'])
                return
        raise RuntimeError(f"Could not find input source for language '{lang_code}'")

    def find_ids(self, query_substr: str) -> list[str]:
        query = query_substr.lower()
        return [
            item['id']
            for item in self.list_sources(include_types=None)
            if query in item['id'].lower() or query in item['name'].lower()
        ]
