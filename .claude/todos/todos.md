- [x] use open ai response api instead of chat completion api
- [x] fix this error 
```
Traceback (most recent call last):
  File "/Users/yusizhang/workspace/inbox-cast/.venv/lib/python3.13/site-packages/readability/readability.py", line 227, in summary
    self._html(True)
    ~~~~~~~~~~^^^^^^
  File "/Users/yusizhang/workspace/inbox-cast/.venv/lib/python3.13/site-packages/readability/readability.py", line 153, in _html
    self.html = self._parse(self.input)
                ~~~~~~~~~~~^^^^^^^^^^^^
  File "/Users/yusizhang/workspace/inbox-cast/.venv/lib/python3.13/site-packages/readability/readability.py", line 166, in _parse
    doc, self.encoding = build_doc(input)
                         ~~~~~~~~~^^^^^^^
  File "/Users/yusizhang/workspace/inbox-cast/.venv/lib/python3.13/site-packages/readability/htmls.py", line 20, in build_doc
    doc = lxml.html.document_fromstring(
        decoded_page.encode("utf-8", "replace"), parser=utf8_parser
    )
  File "/Users/yusizhang/workspace/inbox-cast/.venv/lib/python3.13/site-packages/lxml/html/__init__.py", line 742, in document_fromstring
    raise etree.ParserError(
        "Document is empty")
lxml.etree.ParserError: Document is empty
```

- [x] Fix this warning log
```
To disable this warning, you can either:
        - Avoid using `tokenizers` before the fork if possible
        - Explicitly set the environment variable TOKENIZERS_PARALLELISM=(true | false)
```

- [ ] each generated audio segment should be saved to /out
- [ ] implement more sophisticated paywall detection logic
