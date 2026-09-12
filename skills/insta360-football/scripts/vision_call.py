"""One explicit vision request, with raw response and usage receipt. No model loading."""
import argparse
import base64
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, 'Redirect refused', headers, fp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', default='http://127.0.0.1:1234/v1')
    p.add_argument('--model', required=True)
    p.add_argument('--prompt', type=Path, required=True)
    p.add_argument('--image', action='append', type=Path, required=True)
    p.add_argument('--schema', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-remote', action='store_true')
    p.add_argument('--max-tokens', type=int, default=500)
    a = p.parse_args()
    parsed = urllib.parse.urlparse(a.base_url)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        p.error('Use a plain HTTP(S) API URL without embedded credentials/query/fragment')
    if parsed.hostname not in ('localhost', '127.0.0.1', '::1') and not a.allow_remote:
        p.error('Remote images require explicit consent and --allow-remote')
    if not 1 <= a.max_tokens <= 8192 or not 1 <= len(a.image) <= 8:
        p.error('Bound max-tokens and image count')
    content = [{'type': 'text', 'text': a.prompt.read_text(encoding='utf-8')}]
    for image in a.image:
        if image.suffix.lower() not in ('.jpg', '.jpeg', '.png') or image.stat().st_size > 20_000_000:
            p.error('Use bounded JPG/PNG perspective images')
        mime = 'image/png' if image.suffix.lower() == '.png' else 'image/jpeg'
        content.extend([{'type': 'text', 'text': f'IMAGE {image.name}'},
                        {'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + base64.b64encode(image.read_bytes()).decode()}}])
    payload = {'model': a.model, 'messages': [{'role': 'user', 'content': content}],
               'temperature': 0, 'max_tokens': a.max_tokens}
    if a.schema:
        payload['response_format'] = {'type': 'json_schema', 'json_schema': {
            'name': 'football_observation', 'strict': True,
            'schema': json.loads(a.schema.read_text(encoding='utf-8'))}}
    output = a.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve a unique receipt before contacting the model; failures retain their own receipt.
    with output.open('x', encoding='utf-8') as f:
        started = time.monotonic()
        report = {'model': a.model, 'image_count': len(a.image), 'started_unix': time.time(),
                  'remote': parsed.hostname not in ('localhost', '127.0.0.1', '::1')}
        try:
            request = urllib.request.Request(a.base_url.rstrip('/') + '/chat/completions',
                                             data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.build_opener(NoRedirect).open(request, timeout=180) as response:
                raw = json.loads(response.read())
            report.update(status='completed', response=raw, usage=raw.get('usage'),
                          finish_reason=raw['choices'][0].get('finish_reason'))
        except Exception as exc:
            report.update(status='failed', error_type=type(exc).__name__)
            raise
        finally:
            report['seconds'] = time.monotonic() - started
            json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({'receipt': str(output), 'status': report['status'],
                      'usage': report.get('usage'), 'seconds': report['seconds']}))


if __name__ == '__main__':
    main()
