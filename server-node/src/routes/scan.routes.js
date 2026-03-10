/**
 * Scan routes — upload prescription image, get scan history.
 */
import { Router } from 'express';
import multer from 'multer';
import { asyncHandler } from '../utils/errors.js';
import { success, paginated } from '../utils/response.js';
import { requireAuth } from '../middleware/auth.js';
import { AppError } from '../utils/errors.js';
import * as scanService from '../services/scan.service.js';
import { env } from '../config/env.js';

const router = Router();

// Multer config: memory storage, max 10MB
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: env.MAX_FILE_SIZE_MB * 1024 * 1024 },
});

// Allowed MIME types (magic bytes check in route)
const ALLOWED_MIMES = ['image/jpeg', 'image/png', 'image/webp'];

/**
 * POST /api/scan
 * Upload prescription image → OCR pipeline → drug list.
 * Requires auth. Max 10MB image.
 */
router.post(
  '/',
  requireAuth,
  upload.single('file'),
  asyncHandler(async (req, res) => {
    if (!req.file) {
      throw new AppError('No file uploaded', 400, 'NO_FILE');
    }

    // Check MIME type from magic bytes (not just Content-Type header)
    const { fileTypeFromBuffer } = await import('file-type');
    const detected = await fileTypeFromBuffer(req.file.buffer);
    if (!detected || !ALLOWED_MIMES.includes(detected.mime)) {
      throw new AppError(
        `Invalid file type. Allowed: ${ALLOWED_MIMES.join(', ')}`,
        400,
        'INVALID_FILE_TYPE'
      );
    }

    const result = await scanService.scanPrescription(
      req.file.buffer,
      req.user.sub,
      req.file.originalname,
      detected.mime  // pass verified MIME type
    );

    success(res, result);
  })
);

/**
 * GET /api/scan/history?page=1&limit=20
 * Get scan history for current user.
 */
router.get(
  '/history',
  requireAuth,
  asyncHandler(async (req, res) => {
    const page = parseInt(req.query.page) || 1;
    const limit = Math.min(parseInt(req.query.limit) || 20, 50);

    const result = await scanService.getScanHistory(req.user.sub, { page, limit });
    paginated(res, {
      items: result.scans,
      total: result.total,
      page,
      limit,
    });
  })
);

export default router;
