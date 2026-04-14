import { Router } from 'express';
import { z } from 'zod';

import { requireAuth } from '../middleware/auth.js';
import { validateBody } from '../middleware/validator.js';
import { asyncHandler } from '../utils/errors.js';
import { success } from '../utils/response.js';
import * as reconciliationService from '../services/reconciliation.service.js';

const router = Router();

const scanCompareSchema = z.object({
  scanId: z.string().min(8).max(120),
});

const previousScanCompareSchema = z.object({
  scanId: z.string().min(8).max(120),
  previousScanId: z.string().min(8).max(120).optional(),
});

const dispensedItemSchema = z.object({
  rawName: z.string().max(255).optional(),
  ocrText: z.string().max(255).optional(),
  matchedDrugName: z.string().max(255).optional(),
  mappingStatus: z.enum(['confirmed', 'unmapped_candidate', 'rejected_noise']).optional(),
  confidence: z.number().min(0).max(1).optional(),
  packagingType: z.string().max(80).optional(),
}).refine((item) => Boolean(item.rawName || item.ocrText), {
  message: 'Mỗi mục phải có rawName hoặc ocrText',
});

const dispensedCompareSchema = z.object({
  sourceRef: z.string().max(120).optional(),
  packagingType: z.string().max(80).optional(),
  items: z.array(dispensedItemSchema).min(1),
});

router.post(
  '/scan-vs-active-plan',
  requireAuth,
  validateBody(scanCompareSchema),
  asyncHandler(async (req, res) => {
    const result = await reconciliationService.compareScanToActivePlan(
      req.user.sub,
      req.body.scanId,
    );
    success(res, result);
  })
);

router.post(
  '/scan-vs-previous-scan',
  requireAuth,
  validateBody(previousScanCompareSchema),
  asyncHandler(async (req, res) => {
    const result = await reconciliationService.compareScanToPreviousScan(
      req.user.sub,
      req.body.scanId,
      req.body.previousScanId,
    );
    success(res, result);
  })
);

router.post(
  '/dispensed-text-vs-active-plan',
  requireAuth,
  validateBody(dispensedCompareSchema),
  asyncHandler(async (req, res) => {
    const result = await reconciliationService.compareDispensedTextToActivePlan(
      req.user.sub,
      req.body,
    );
    success(res, result);
  })
);

export default router;
