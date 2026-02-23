import requests
import re
from typing import List

from .config import (
    CHUNK_SIZE,
    CONFLUENCE_API_TOKEN,
    CONFLUENCE_BASE_URL,
    CONFLUENCE_EMAIL,
    PDF_PATH,
)
from .embeddings import embed_texts
from pathlib import Path
import PyPDF2
from pdf2image import convert_from_path
import pytesseract


def fetch_confluence_pages(space_key: str, limit: int = 200) -> List[dict]:
    """
    Fetch pages from a Confluence space using the REST API.
    Requires CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN if the space is private.
    """
    results = []
    start = 0
    base_url = CONFLUENCE_BASE_URL.rstrip("/")
    url = f"{base_url}/rest/api/content"
    auth = (
        (CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)
        if CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN
        else None
    )
    params = {
        "spaceKey": space_key,
        "expand": "body.storage",
        "limit": 50,
        "type": "page",
    }

    while True:
        params["start"] = start

        r = requests.get(url, params=params, auth=auth)
        r.raise_for_status()
        data = r.json()

        items = data.get("results", [])
        if not items:
            break

        for item in items:
            title = item.get("title")
            if idx == 0:
                print("Title: ", title)
                print("Body: ", body)
            page_id = item.get("id")
            body = item.get("body", {}).get("storage", {}).get("value", "")
            text = _html_to_text(body)

            results.append({
                "id": page_id,
                "title": title,
                "text": text,
            })

        start += params["limit"]
        if start >= limit:
            break

        # Stop if the API indicates there are no more pages
        if data.get("size", 0) < params["limit"]:
            break

    return results


def _html_to_text(html: str) -> str:
    """
    Very naive HTML -> text stripper.
    For production use, consider BeautifulSoup.
    """
    clean = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S)
    clean = re.sub(r"<style.*?>.*?</style>", "", clean, flags=re.S)
    clean = re.sub(r"<[^<]+?>", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = 50,
) -> List[str]:
    """
    Chunk text into overlapping windows by characters.
    Returns list of chunk strings.
    """
    text = text.strip()

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def build_corpus_and_embeddings(pages: List[dict]):
    """
    Given list of pages from Confluence, produce chunks,
    compute embeddings and metadata list.
    """
    all_chunks = []
    metadatas = []
    texts_to_embed = []

    for idx, p in enumerate(pages):
        if idx == 0:
            print(p["text"])
        chunks = chunk_text(p["text"]) if p.get("text") else []
        if idx == 0:
            print("Chunks: ", chunks)

        for i, c in enumerate(chunks):
            if idx == 0:
                print("Chunk: ", c)
            meta = {
                "page_id": p["id"],
                "title": p["title"],
                "chunk_index": i,
            }
            all_chunks.append(c)
            metadatas.append(meta)
            texts_to_embed.append(c)

    # Compute embeddings in batches
    batch_size = 16
    vectors = []

    for i in range(0, len(texts_to_embed), batch_size):
        batch = texts_to_embed[i:i + batch_size]
        vs = embed_texts(batch)
        vectors.extend(vs)

    return all_chunks, metadatas, vectors


def load_pdf_pages(pdf_path: str = PDF_PATH) -> List[dict]:
    """
    Load one or more PDF files and return a list of page dicts matching the shape
    expected by build_corpus_and_embeddings.

    Behavior:
    - Resolve the configured PDF_PATH (file) via common fallbacks.
    - Load that file AND any other PDFs living in the same directory.
      This lets you drop multiple onboarding PDFs into app/data and have
      them all indexed together.
    """
    # Try the provided path and a couple of common fallbacks inside the container.
    candidate_paths = [
        Path(pdf_path),
        Path("/app/data") / Path(pdf_path).name,
        Path("/app/app/data") / Path(pdf_path).name,
    ]

    root_path = next((p for p in candidate_paths if p.exists()), None)
    if root_path is None:
        raise FileNotFoundError(
            f"PDF path not found. Tried: {[str(p) for p in candidate_paths]}"
        )

    # Determine which PDF files to load:
    pdf_files = []
    if root_path.is_dir():
        pdf_files = sorted(root_path.glob("*.pdf"))
    else:
        # Always include the configured file itself...
        pdf_files.append(root_path)
        # ...and also any other PDFs in the same directory.
        pdf_files.extend(
            sorted(p for p in root_path.parent.glob("*.pdf") if p.name != root_path.name)
        )

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found near: {root_path}")

    pages: List[dict] = []

    for pdf in pdf_files:
        # Pre-render all pages as images once for this PDF (used for OCR fallback)
        try:
            images = convert_from_path(str(pdf), dpi=300)
        except Exception as e:
            print(f"[PDF] Failed to render images for {pdf}: {e}")
            images = []

        with pdf.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            local_count = 0
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""

                # Try to extract hyperlinks from the page
                links_text = ""
                try:
                    if "/Annots" in page:
                        annotations = page["/Annots"]
                        for annotation in annotations:
                            annotation_obj = annotation.get_object()
                            if annotation_obj.get("/Subtype") == "/Link":
                                uri = annotation_obj.get("/A", {}).get("/URI")
                                if uri:
                                    links_text += f" [Link: {uri}]\n"
                except Exception as e:
                    # Link extraction is optional, don't fail if it doesn't work
                    pass

                # Fallback to OCR if we didn't get any text
                if not text.strip() and idx < len(images):
                    try:
                        text = pytesseract.image_to_string(images[idx]) or ""
                    except Exception as e:
                        print(f"[OCR] Failed on {pdf} page {idx}: {e}")

                # Append link information to the text if found
                if links_text:
                    text = text + "\n\n" + links_text

                # If still empty, skip this page so we don't pollute the index
                if not text.strip():
                    continue

                pages.append(
                    {
                        "id": f"{pdf.name}-page-{idx}",
                        "title": pdf.name,
                        "text": text,
                    }
                )
                local_count += 1

        # Log loaded pages for each PDF for visibility
        print(f"[PDF] Loaded {local_count} pages with text from {pdf}")

    # Optional: log a short preview of each page (can be noisy for many PDFs)
    for p in pages:
        print({"id": p["id"], "title": p["title"], "text_preview": p["text"][:2000]})

    return pages
