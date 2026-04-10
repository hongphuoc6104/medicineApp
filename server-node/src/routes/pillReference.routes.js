import { Router } from 'express';
import multer from 'multer';
import { z } from 'zod';

import { requireAuth } from '../middleware/auth.js';
import { validateBody, validateQuery } from '../middleware/validator.js';
import { asyncHandler, AppError } from '../utils/errors.js';
import { created, success } from '../utils/response.js';
import { env } from '../config/env.js';
import * as pillReferenceService from '../services/pillReference.service.js';

const router = Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: env.MAX_FILE_SIZE_MB * 1024 * 1024 },
});

const ALLOWED_MIMES = ['image/jpeg', 'image/png', 'image/webp'];

const enrollStartSchema = z.object({
  planId: z.string().uuid(),
  drugNameSnapshot: z.string().min(1).max(255).optional(),
});

const frameSchema = z.object({
  side: z.enum(['front', 'back', 'other']).optional(),
  qualityScore: z.coerce.number().min(0).max(1).optional(),
});

const finalizeSchema = z.object({
  confirmedImageIds: z.array(z.string().uuid()).optional(),
});

router.post(
  '/enroll/start',
  requireAuth,
  validateBody(enrollStartSchema),
  asyncHandler(async (req, res) => {
    const data = await pillReferenceService.startEnrollment(req.user.sub, req.body);
    created(res, data);
  })
);

router.post(
  '/:id/frame',
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

    const parsed = frameSchema.safeParse(req.body || {});
    if (!parsed.success) {
      throw new AppError('Dữ liệu khung ảnh không hợp lệ', 400, 'VALIDATION_ERROR');
    }

    const framePayload = parsed.data;
    const data = await pillReferenceService.uploadEnrollmentFrame(
      req.params.id,
      req.user.sub,
      req.file.buffer,
      req.file.originalname,
      detected.mime,
      framePayload
    );
    success(res, data);
  })
);

router.post(
  '/:id/finalize',
  requireAuth,
  validateBody(finalizeSchema),
  asyncHandler(async (req, res) => {
    const data = await pillReferenceService.finalizeEnrollment(
      req.params.id,
      req.user.sub,
      req.body
    );
    success(res, data);
  })
);

router.get(
  '/',
  requireAuth,
  validateQuery(
    z.object({
      planId: z.string().uuid().optional(),
    })
  ),
  asyncHandler(async (req, res) => {
    const planId = typeof req.query.planId === 'string' ? req.query.planId : null;
    const data = await pillReferenceService.listReferenceSets(req.user.sub, {
      planId,
    });
    success(res, data);
  })
);

export default router;
