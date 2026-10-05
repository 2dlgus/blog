# hyeonlee.net

`content/posts/{번호}.html` 파일 하나가 글 하나입니다. main 브랜치에 올리면 자동으로 빌드·배포됩니다.

## 글 파일 형식

```html
<!--
id: 152
제목: 글 제목
카테고리: Stack/Lowcode
태그: Mendix, SSO
날짜: 2026-10-10 09:00
형식: pc
썸네일: /img/t/파일명.webp
공개: Y
-->
<article>…본문 HTML…</article>
```

- 주소는 `https://hyeonlee.net/{id}` 입니다.
- `공개: N` 이면 빌드에서 빠집니다.
- `형식: pc` 는 사이트 공통 컴포넌트(`pc-lead`, `pc-table`, `pc-note`, `pc-cols`, `pc-steps` 등, `static/base.css`)를 쓰는 새 글입니다. 다크모드가 자동으로 적용됩니다.
- 시리즈는 `config.json` 의 `series` 에 제목·본문 패턴으로 묶습니다.
- 이미지는 `static/img/` 에 넣고 `/img/파일명` 으로 씁니다.
- 메뉴 순서·시리즈·광고·댓글 설정은 `config.json` 에 있습니다.

## 로컬 미리보기

```
python build.py
python -m http.server -d dist 8000
```
