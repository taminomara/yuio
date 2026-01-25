function initAnnotationTooltips() {
  const containers = document.querySelectorAll("div.annotate.highlight");

  containers.forEach((container) => {
    const codeBlock = container.querySelector("pre");

    if (!codeBlock) return;

    const annotationList = container.parentElement.querySelector("ol");
    const annotations = Array.from(
      annotationList?.querySelectorAll("li") ?? []
    );

    replaceMarkersWithTooltips(codeBlock, annotations);
  });

  // Global click handler to dismiss tooltips when clicking outside
  document.addEventListener("click", (e) => {
    if (
      !e.target.closest(".annotation-trigger") &&
      !e.target.closest(".annotation-tooltip")
    ) {
      hideAllTooltips();
    }
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideAllTooltips();
    }
  });
}

function hideAllTooltips() {
  document
    .querySelectorAll(".annotation-tooltip.visible")
    .forEach((tooltip) => {
      tooltip.classList.remove("visible");
      const triggerId = tooltip.getAttribute("data-trigger-id");
      const trigger = document.getElementById(triggerId);
      if (trigger) {
        trigger.setAttribute("aria-expanded", "false");
      }
    });
}

function replaceMarkersWithTooltips(element, annotations) {
  const walker = document.createTreeWalker(
    element,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );

  const textNodes = [];
  let node;
  while ((node = walker.nextNode())) {
    textNodes.push(node);
  }

  textNodes.forEach((textNode) => {
    const text = textNode.textContent;
    const regex = /\s*\[((?:\\.|[^\]])+)\]_\s*/g;

    if (!regex.test(text)) return;
    regex.lastIndex = 0;

    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        fragment.appendChild(
          document.createTextNode(text.slice(lastIndex, match.index))
        );
      }

      const reference = match[1];
      const annotationIndex = parseInt(match[1], 10) - 1;
      let annotation = annotations[annotationIndex];
      if (annotation) {
        const div = document.createElement("div");
        div.append(...annotation.children);
        annotation = div;
      } else {
        annotation = document.createElement("p");
        annotation.appendChild(document.createTextNode(reference));
      }

      const trigger = createTooltipTrigger(annotation);
      fragment.appendChild(trigger);

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    textNode.parentNode.replaceChild(fragment, textNode);
  });
}

function createTooltipTrigger(annotation) {
  const uniqueId = `annotation-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2, 9)}`;
  const tooltipId = `${uniqueId}-tooltip`;
  const triggerId = `${uniqueId}-trigger`;

  // Create trigger button
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.id = triggerId;
  trigger.className = "annotation-trigger";
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-haspopup", "true");
  trigger.setAttribute("aria-controls", tooltipId);

  // Create tooltip in body
  const tooltip = document.createElement("div");
  tooltip.id = tooltipId;
  tooltip.className = "annotation-tooltip";
  tooltip.setAttribute("role", "tooltip");
  tooltip.setAttribute("data-trigger-id", triggerId);
  tooltip.appendChild(annotation);
  document.body.appendChild(tooltip);

  // Click to toggle
  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    const isCurrentlyVisible = tooltip.classList.contains("visible");

    // Hide all other tooltips first
    hideAllTooltips();

    if (!isCurrentlyVisible) {
      showTooltip(trigger, tooltip);
    }
  });

  // Keyboard support
  trigger.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      trigger.click();
    }
  });

  return trigger;
}

function showTooltip(trigger, tooltip) {
  tooltip.classList.add("visible");
  trigger.setAttribute("aria-expanded", "true");
  positionTooltip(trigger, tooltip);
}

function positionTooltip(trigger, tooltip) {
  const triggerRect = trigger.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const scrollX = window.scrollX;
  const scrollY = window.scrollY;
  const gap = 4;

  // Default: position below the trigger
  let top = triggerRect.bottom + scrollY + gap;
  let left = triggerRect.left + scrollX;

  // Check horizontal overflow
  if (left + tooltipRect.width > (4 * viewportWidth) / 5 + scrollX - 10) {
    left = triggerRect.left + scrollX - tooltipRect.width + triggerRect.width;
  }
  if (left < scrollX + 10) {
    left = scrollX + 10;
  }

  // Check vertical overflow - flip above if needed
  if (triggerRect.bottom + tooltipRect.height + gap > viewportHeight) {
    top = triggerRect.top + scrollY - tooltipRect.height - gap;
    tooltip.classList.add("above");
  } else {
    tooltip.classList.remove("above");
  }

  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${left}px`;
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAnnotationTooltips);
} else {
  initAnnotationTooltips();
}
