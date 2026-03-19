import { Router } from 'express';
import multer from 'multer';
import { z } from 'zod';

import { requireAuth } from '../middleware/auth.js';
import { validateBody } from '../middleware/validator.js';
import { asyncHandler, AppError } from '../utils/errors.js';
import { created, success } from '../utils/response.js';
import * as pillVerificationService from '../services/pillVerification.service.js';
import { env } from '../config/env.js';

const router = Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: env.MAX_FILE_SIZE_MB * 1024 * 1024 },
});

const ALLOWED_MIMES = ['image/jpeg', 'image/png', 'image/webp'];

const startSchema = z.object({
  occurrenceId: z.string().min(3).max(120),
  planId: z.string().min(3),
  scheduledTime: z.string().datetime(),
  expectedMedications: z.array(z.object({
    planId: z.string().min(3).optional(),
    drugName: z.string().min(1),
    dosage: z.string().optional(),
    pillsPerDose: z.number().int().min(1).optional(),
  })).min(1),
});

const assignSchema = z.object({
  detectionIdx: z.number().int().min(0),
  assignedDrugName: z.string().max(255).nullable().optional(),
  status: z.enum(['assigned', 'unknown', 'extra']),
  note: z.string().max(500).optional(),
});

router.post(
  '/start',
  requireAuth,
  validateBody(startSchema),
  asyncHandler(async (req, res) => {
    const session = await pillVerificationService.startSession(req.user.sub, req.body);
    created(res, session);
  })
);

router.post(
  '/:id/image',
  requireAuth,
  upload.single('file'),
  asyncHandler(async (req, res) => {
    if (!req.file) {
      throw new AppError('No file uploaded', 400, 'NO_FILE');
    }

    const { fileTypeFromBuffer } = await import('file-type');
    const detected = await fileTypeFromBuffer(req.file.buffer);
    if (!detected || !ALLOWED_MIMES.includes(detected.mime)) {
      throw new AppError(
        `Invalid file type. Allowed: ${ALLOWED_MIMES.join(', ')}`,
        400,
        'INVALID_FILE_TYPE'
      );
    }

    const session = await pillVerificationService.uploadImage(
      req.params.id,
      req.user.sub,
      req.file.buffer,
      req.file.originalname,
      detected.mime
    );
    success(res, session);
  })
);

router.post(
  '/:id/assign',
  requireAuth,
  validateBody(assignSchema),
  asyncHandler(async (req, res) => {
    const session = await pillVerificationService.assignDetection(
      req.params.id,
      req.user.sub,
      req.body
    );
    success(res, session);
  })
);

router.post(
  '/:id/confirm',
  requireAuth,
  asyncHandler(async (req, res) => {
    const session = await pillVerificationService.confirmSession(req.params.id, req.user.sub);
    success(res, session);
  })
);

router.get(
  '/:id',
  requireAuth,
  asyncHandler(async (req, res) => {
    const session = await pillVerificationService.getSession(req.params.id, req.user.sub);
    success(res, session);
  })
);

export default router;
