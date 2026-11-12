import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

from py3s_codec import (
    CRC32_FIELD_OFFSET,
    FLAG_AI_SYSTEM_PROMPT,
    FLAG_INTEGRITY_CRC32,
    FLAG_MFG_PRINT3D_READY,
    FLAG_PRINT_3MF,
    FLAG_SECURITY_HMAC,
    MAX_METADATA_BYTES,
    Py3sContainer,
    compute_container_crc32,
    sanitize_filename_token,
    validate_safe_zip_bytes,
)


class PrintContainerTests(unittest.TestCase):
    def test_print_roundtrip_and_legacy(self):
        metadata = {'format': 'py3s', 'version': '1.1.0', 'asset': {'name': 'test'}}
        packed = Py3sContainer.pack(b'visual', b'collider', metadata, b'thumbnail', b'print')
        container = Py3sContainer.unpack(packed)
        self.assertEqual(container.print_3mf_data, b'print')
        self.assertEqual(container.spz_data, b'visual')
        self.assertEqual(container.collider_data, b'collider')
        self.assertEqual(container.thumbnail_data, b'thumbnail')
        self.assertEqual(container.metadata, metadata)
        self.assertEqual(struct.unpack_from('<H', packed, 6)[0], 1)
        self.assertEqual(struct.unpack_from('<I', packed, 8)[0], 5)
        legacy = Py3sContainer.pack(b'visual', b'collider', metadata)
        self.assertEqual(struct.unpack_from('<H', legacy, 6)[0], 0)
        self.assertEqual(Py3sContainer.unpack(legacy).print_3mf_data, b'')

    def test_rejects_truncated_and_overlapping_payload(self):
        packed = Py3sContainer.pack(b'visual', b'collider', {}, print_3mf_bytes=b'print')
        with self.assertRaisesRegex(ValueError, 'section range'):
            Py3sContainer.unpack(packed[:-1])
        overlapping = bytearray(packed)
        struct.pack_into('<Q', overlapping, 80, 128)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            Py3sContainer.unpack(overlapping)

    def test_cli_preserves_prepared_3mf(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root = Path(directory)
            (root / 'visual.spz').write_bytes(b'visual')
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as target:
                target.writestr('3D/3dmodel.model', '<model/>')
            (root / 'print.3mf').write_bytes(archive.getvalue())
            cli = Path(__file__).with_name('py3s_codec.py')
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            def run(*arguments):
                return subprocess.run([sys.executable, str(cli), *map(str, arguments)], check=True, capture_output=True, env=env)
            output = root / 'test.py3s'
            run('pack', '--spz', root / 'visual.spz', '--print-3mf', root / 'print.3mf', '-o', output)
            run('unpack', output, '-d', root / 'extracted')
            self.assertEqual((root / 'extracted' / 'test_print.3mf').read_bytes(), archive.getvalue())
            self.assertIn(b'Print 3MF', run('info', output).stdout)

    def test_v2_crc32_verification_and_flags(self):
        metadata = {
            'format': 'py3s',
            'version': '2.0.0',
            'asset': {'name': 'nasa_v2_check'},
            'systemPrompt': 'Print with PETG-CF at 0.16 mm.',
            'aiAgentContext': {'orchestratedBy': 'Hanuman-1.5'},
        }
        packed = Py3sContainer.pack(b'visual_v2', b'collider_v2', metadata, b'', b'PK\x03\x04print')
        container = Py3sContainer.unpack(packed)
        self.assertEqual(container.version_major, 2)
        self.assertEqual(container.version_minor, 0)
        self.assertTrue(container.flags & FLAG_PRINT_3MF)
        self.assertTrue(container.flags & FLAG_MFG_PRINT3D_READY)
        self.assertTrue(container.flags & FLAG_AI_SYSTEM_PROMPT)
        self.assertTrue(container.flags & FLAG_INTEGRITY_CRC32)
        self.assertGreater(container.container_crc32, 0)
        self.assertGreater(container.print_3mf_crc32, 0)

        corrupted = bytearray(packed)
        corrupted[-1] ^= 0x01
        with self.assertRaisesRegex(ValueError, 'CRC32 mismatch'):
            Py3sContainer.unpack(bytes(corrupted))

    def test_security_metadata_zip_creality_and_hmac(self):
        # 1. Prototype pollution key sanitization & depth/size caps
        hostile_meta = json.loads(
            '{"format":"py3s","version":"2.0.0","asset":{"name":"sec"},"__proto__":{"polluted":true},"nested":{"constructor":"bad","safe":1}}'
        )
        packed_meta = Py3sContainer.pack(b'spz', b'', hostile_meta)
        unpacked_meta = Py3sContainer.unpack(packed_meta)
        self.assertNotIn('__proto__', unpacked_meta.metadata)
        self.assertNotIn('constructor', unpacked_meta.metadata['nested'])
        self.assertEqual(unpacked_meta.metadata['nested']['safe'], 1)

        deep = {'leaf': True}
        for _ in range(28):
            deep = {'child': deep}
        deep_packed = Py3sContainer.pack(
            b'spz',
            b'',
            {'format': 'py3s', 'version': '2.0.0', 'asset': {'name': 'deep'}, 'extra': deep},
        )
        with self.assertRaisesRegex(ValueError, 'nesting depth'):
            Py3sContainer.unpack(deep_packed)

        with self.assertRaisesRegex(ValueError, 'maximum safe size'):
            Py3sContainer.pack(
                b'spz',
                b'',
                {'format': 'py3s', 'version': '2.0.0', 'asset': {'name': 'huge', 'blob': 'x' * (MAX_METADATA_BYTES + 64)}},
            )

        # 2. Zip Slip, XXE <!DOCTYPE>, and Zip Bomb protection
        slip_zip = io.BytesIO()
        with zipfile.ZipFile(slip_zip, 'w') as zf:
            zf.writestr('../../../evil.model', '<model/>')
        with self.assertRaisesRegex(ValueError, 'Zip Slip'):
            validate_safe_zip_bytes(slip_zip.getvalue(), require_3mf_model=False)

        xxe_zip = io.BytesIO()
        with zipfile.ZipFile(xxe_zip, 'w') as zf:
            zf.writestr('3D/3dmodel.model', '<?xml version="1.0"?><!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]><model/>')
        with self.assertRaisesRegex(ValueError, 'XML directive'):
            validate_safe_zip_bytes(xxe_zip.getvalue(), require_3mf_model=True)

        # 3. HMAC-SHA256 signing, verification, and tamper detection
        valid_3mf = io.BytesIO()
        with zipfile.ZipFile(valid_3mf, 'w') as zf:
            zf.writestr('3D/3dmodel.model', '<model unit="millimeter"></model>')

        secret = 'unit-test-py3s-hmac-key'
        signed = Py3sContainer.pack_signed(
            b'visual_signed',
            b'collider_signed',
            {'format': 'py3s', 'version': '2.0.0', 'asset': {'name': '../../etc/../../nasa_part'}},
            secret_key=secret,
            print_3mf_bytes=valid_3mf.getvalue(),
        )
        unauth = Py3sContainer.unpack(signed)
        self.assertTrue(unauth.flags & FLAG_SECURITY_HMAC)
        self.assertTrue(Py3sContainer.verify_signature(signed, secret))
        self.assertFalse(Py3sContainer.verify_signature(signed, 'wrong-key'))
        verified = Py3sContainer.unpack_verified(signed, secret)
        self.assertEqual(verified.spz_data, b'visual_signed')

        tampered = bytearray(signed)
        tampered[0x68] ^= 0xFF
        self.assertFalse(Py3sContainer.verify_signature(bytes(tampered), secret))
        with self.assertRaisesRegex(ValueError, 'CRC32 mismatch'):
            Py3sContainer.unpack_verified(bytes(tampered), secret)

        # Even if an attacker mutates payload and recomputes valid CRC-32, HMAC rejects the forgery
        forged = bytearray(signed)
        forged[128] ^= 0x01
        struct.pack_into('<I', forged, CRC32_FIELD_OFFSET, compute_container_crc32(bytes(forged)))
        self.assertEqual(len(Py3sContainer.unpack(bytes(forged)).spz_data), len(b'visual_signed'))
        self.assertFalse(Py3sContainer.verify_signature(bytes(forged), secret))
        with self.assertRaisesRegex(ValueError, 'HMAC signature'):
            Py3sContainer.unpack_verified(bytes(forged), secret)

        # 4. Creality Bridge path confinement & strict Print 3D enforcement
        bridge_path = Path(__file__).resolve().parent / 'py3s_creality_bridge.py'
        spec = importlib.util.spec_from_file_location('py3s_creality_bridge_test', str(bridge_path))
        bridge_mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(bridge_mod)

        self.assertEqual(sanitize_filename_token('../../evil\\part..name'), 'part_name')
        with tempfile.TemporaryDirectory() as tmp:
            py3s_file = Path(tmp) / 'signed_asset.py3s'
            py3s_file.write_bytes(signed)
            out_path = bridge_mod.send_py3s_to_creality(
                str(py3s_file),
                auto_launch=False,
                secret_key=secret,
                require_signature=True,
            )
            try:
                self.assertEqual(os.path.dirname(os.path.abspath(out_path)), os.path.abspath(tempfile.gettempdir()))
                self.assertEqual(os.path.basename(out_path), 'nasa_part_creality.3mf')
            finally:
                if os.path.exists(out_path):
                    os.remove(out_path)

            # Reject unsigned or collider-only files instead of masquerading collider as .3mf
            collider_only = Path(tmp) / 'collider_only.py3s'
            collider_only.write_bytes(Py3sContainer.pack(b'spz', b'glb_bytes', {'format': 'py3s', 'version': '2.0.0', 'asset': {'name': 'no_print'}}))
            with self.assertRaisesRegex(ValueError, 'No Print 3D'):
                bridge_mod.send_py3s_to_creality(str(collider_only), auto_launch=False)

    def test_compatible_v1_header_and_local_print_cache_bridge(self):
        # 1. compatible_v1 emits clean v1.0 headers while keeping v2 JSON metadata
        v1_compat = Py3sContainer.pack(
            b'spz_payload',
            b'glb_payload',
            {
                'format': 'py3s',
                'version': '1.0.0',
                'asset': {'name': 'thai-temple-gate'},
                'collision': {'format': 'glb'},
                'systemPrompt': 'Print cleanly at 0.16 mm.',
                'printProfile': {'material': 'PLA', 'layerHeightMm': 0.16, 'infillPercent': 20},
                'aiAgentContext': {'orchestratedBy': 'Hanuman-1.5'},
            },
            thumbnail_bytes=b'png',
            compatible_v1=True,
        )
        unpacked = Py3sContainer.unpack(v1_compat)
        self.assertEqual(unpacked.version_major, 1)
        self.assertEqual(unpacked.version_minor, 0)
        self.assertEqual(unpacked.flags, 0x03)
        self.assertEqual(v1_compat[0x50:0x80], b'\x00' * 0x30)
        self.assertEqual(unpacked.metadata['systemPrompt'], 'Print cleanly at 0.16 mm.')

        # 2. Local print-cache hydration in Creality Print bridge without embedding huge 3MF inside .py3s
        bridge_path = Path(__file__).resolve().parent / 'py3s_creality_bridge.py'
        spec = importlib.util.spec_from_file_location('py3s_creality_bridge_cache_test', str(bridge_path))
        bridge_mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(bridge_mod)

        valid_3mf = io.BytesIO()
        with zipfile.ZipFile(valid_3mf, 'w') as zf:
            zf.writestr('3D/3dmodel.model', '<model unit="millimeter"></model>')

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cache_dir = tmp_path / '.pygrassreal' / 'print-cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / 'gate_cached.3mf').write_bytes(valid_3mf.getvalue())

            cached_py3s = tmp_path / 'gate_seed.py3s'
            cached_py3s.write_bytes(
                Py3sContainer.pack(
                    b'spz_payload',
                    b'glb_payload',
                    {
                        'format': 'py3s',
                        'version': '1.0.0',
                        'asset': {'name': 'gate_cached_model'},
                        'printing': {
                            'format': '3mf',
                            'unit': 'millimeter',
                            'heightMm': 150,
                            'source': 'local-print-cache',
                            'validation': 'closed-oriented-edge-manifold',
                            'cacheKey': 'gate_cached.3mf',
                            'requiresSlicerReview': True,
                        },
                    },
                    compatible_v1=True,
                )
            )

            orig_expanduser = os.path.expanduser
            try:
                os.path.expanduser = lambda path: str(tmp_path) + path[1:] if path.startswith('~') else orig_expanduser(path)
                out_path = bridge_mod.send_py3s_to_creality(str(cached_py3s), auto_launch=False)
                self.assertTrue(os.path.isfile(out_path))
                if os.path.exists(out_path):
                    os.remove(out_path)
            finally:
                os.path.expanduser = orig_expanduser


if __name__ == '__main__':
    unittest.main()
