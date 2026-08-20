// PdfViewerWithOverlay — FRONTEND.md §4.12
// react-pdf wrapper with bbox highlight support
// Used in §3.6 review detail view for field-level source highlighting
import { useState, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/esm/Page/AnnotationLayer.css";
import "react-pdf/dist/esm/Page/TextLayer.css";
import styles from "./PdfViewerWithOverlay.module.css";

pdfjs.GlobalWorkerOptions.workerSrc =
  "//unpkg.com/pdfjs-dist@" + pdfjs.version + "/build/pdf.worker.min.mjs";

interface BBoxHighlight {
  fieldName: string;
  page: number;
  bbox: [number, number, number, number];
  confidence?: number;
}

interface PdfViewerWithOverlayProps {
  url: string;
  highlights?: BBoxHighlight[];
  activeField?: string | null;
  onFieldClick?: (fieldName: string) => void;
}

export default function PdfViewerWithOverlay({
  url,
  highlights = [],
  activeField = null,
  onFieldClick,
}: PdfViewerWithOverlayProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages: n }: { numPages: number }) => {
      setNumPages(n);
      setCurrentPage(1);
    },
    [],
  );

  const pageHighlights = highlights.filter((h) => h.page === currentPage);

  return (
    <div className={styles.container}>
      <div className={styles.controls}>
        <button
          type="button"
          className={styles.pageBtn}
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage <= 1}
          aria-label="Previous page"
        >
          {"<"}
        </button>
        <span className={styles.pageInfo} data-mono>
          {currentPage} / {numPages ?? "?"}
        </span>
        <button
          type="button"
          className={styles.pageBtn}
          onClick={() =>
            setCurrentPage((p) => Math.min(numPages ?? p, p + 1))
          }
          disabled={numPages != null && currentPage >= numPages}
          aria-label="Next page"
        >
          {">"}
        </button>
      </div>
      <div className={styles.viewer}>
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={(error) => console.error("PDF load error:", error)}
        >
          <Page
            pageNumber={currentPage}
            renderTextLayer={true}
            renderAnnotationLayer={true}
            width={600}
          />
        </Document>
        {pageHighlights.length > 0 && (
          <div className={styles.overlay}>
            {pageHighlights.map((h) => {
              const isActive = h.fieldName === activeField;
              const cls =
                styles.highlight + (isActive ? " " + styles.active : "");
              return (
                <div
                  key={h.fieldName}
                  className={cls}
                  style={{
                    left: h.bbox[0] + "px",
                    top: h.bbox[1] + "px",
                    width: h.bbox[2] + "px",
                    height: h.bbox[3] + "px",
                  }}
                  onClick={() => onFieldClick?.(h.fieldName)}
                  role="button"
                  tabIndex={0}
                  aria-label={
                    "Field " +
                    h.fieldName +
                    (h.confidence != null
                      ? ", confidence " +
                        Math.round(h.confidence * 100) +
                        " percent"
                      : "")
                  }
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
